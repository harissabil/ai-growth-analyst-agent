from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any, Dict, List, Optional

from azure.cosmos.exceptions import CosmosResourceNotFoundError

from app.storage.cosmos_db import cosmos_client
from app.storage.cosmos_models import ChatHistoryDocument, ChatHistoryWithMessages, ChatMessageDocument


class ChatRepository:
    """Repository for chat history and message operations."""

    def __init__(self):
        self.client = cosmos_client
        self.executor = ThreadPoolExecutor(max_workers=10)

    def _derive_title(self, text: str, max_len: int = 60) -> str:
        """Derive a title from the first message text."""
        t = " ".join(text.strip().split())
        return t[:max_len] + ("…" if len(t) > max_len else "")

    async def ensure_history(self, chat_history_id: Optional[str], user_id: Optional[str], title_hint: str) -> str:
        """Ensure a chat history exists or create a new one."""
        history_container = self.client.get_history_container()

        if chat_history_id:
            try:
                # Update existing history's updated_at timestamp
                partition_key = user_id or "anonymous"
                existing = history_container.read_item(item=chat_history_id, partition_key=partition_key)
                existing["updated_at"] = datetime.utcnow().isoformat()
                history_container.upsert_item(existing)
                return chat_history_id
            except CosmosResourceNotFoundError:
                # History doesn't exist, create new one
                pass

        # Create new history document
        history_doc = ChatHistoryDocument(user_id=user_id or "anonymous", title=self._derive_title(title_hint))
        history_doc.id = history_doc.chat_history_id  # Ensure id matches

        created_doc = history_container.create_item(body=history_doc.model_dump())
        return created_doc["chat_history_id"]

    async def save_messages_batch(
        self,
        chat_history_id: str,
        messages: List[Any],
        tables_by_assistant_idx: Dict[int, List[Any]],
        user_id: Optional[str] = None,
    ) -> None:
        """Save only NEW messages to Cosmos DB by comparing with existing messages."""
        messages_container = self.client.get_messages_container()
        history_container = self.client.get_history_container()

        # Get all existing messages to compare content
        existing_messages_query = """
                                  SELECT c.role, c.message, c.sequence
                                  FROM c
                                  WHERE c.chat_history_id = @chat_history_id
                                  ORDER BY c.sequence ASC \
                                  """
        params = [{"name": "@chat_history_id", "value": chat_history_id}]

        try:
            existing_result = list(
                messages_container.query_items(
                    query=existing_messages_query, parameters=params, enable_cross_partition_query=False
                )
            )

            # Convert existing messages to comparable format
            existing_messages = []
            current_max_seq = 0
            for msg in existing_result:
                # Skip tool messages that shouldn't be compared
                if msg.get("role") != "tool":
                    existing_messages.append({"role": msg.get("role"), "content": msg.get("message", "").strip()})
                current_max_seq = max(current_max_seq, msg.get("sequence", 0))

        except Exception:
            # Fallback to safe defaults if query fails
            existing_messages = []
            current_max_seq = 0

        # Convert incoming messages to comparable format (skip tool messages)
        incoming_messages = []
        incoming_to_original_idx = {}  # Map filtered index to original index

        for i, m in enumerate(messages):
            role = getattr(m, "type", None) or getattr(m, "role", None) or m.__class__.__name__.lower()
            if role in ("ai", "assistant"):
                role = "assistant"
            elif role in ("human", "user"):
                role = "user"
            elif role in ("tool",):
                continue  # Skip tool messages in comparison
            elif role in ("system",):
                role = "system"
            else:
                role = "assistant" if "AIMessage" in str(type(m)) else "user"

            content = getattr(m, "content", "")
            if not isinstance(content, str):
                content = str(content)

            # Skip empty assistant messages
            if role == "assistant" and not content.strip():
                continue

            incoming_to_original_idx[len(incoming_messages)] = i
            incoming_messages.append({"role": role, "content": content.strip()})

        # Find how many messages at the start are identical
        matching_count = 0
        min_length = min(len(existing_messages), len(incoming_messages))

        for i in range(min_length):
            existing = existing_messages[i]
            incoming = incoming_messages[i]

            if existing["role"] == incoming["role"] and existing["content"] == incoming["content"]:
                matching_count += 1
            else:
                break

        # Only process the NEW messages (beyond the matching ones)
        new_messages_to_save = incoming_messages[matching_count:]

        if not new_messages_to_save:
            return  # Nothing new to save

        # Process and save NEW messages
        message_docs = []
        seq = current_max_seq + 1

        for i, msg_data in enumerate(new_messages_to_save):
            # Map back to original index for table lookup
            filtered_index = matching_count + i
            original_index = incoming_to_original_idx.get(filtered_index, -1)

            # Create message document
            msg_doc = ChatMessageDocument(
                chat_history_id=chat_history_id,
                sequence=seq,
                role=msg_data["role"],
                message=msg_data["content"],
                tables=None,
            )
            msg_doc.id = msg_doc.chat_message_id

            # Attach tables if this is an assistant message with tables
            if original_index in tables_by_assistant_idx and msg_data["role"] == "assistant":
                tables = tables_by_assistant_idx[original_index]
                if tables:
                    msg_doc.tables = [t.model_dump() for t in tables]

            message_docs.append(msg_doc)
            seq += 1

        if not message_docs:
            return  # No valid messages to save

        # Save the new messages
        batch_errors = []

        try:
            # Insert new messages
            for doc in message_docs:
                try:
                    messages_container.create_item(body=doc.model_dump())
                except Exception as e:
                    batch_errors.append(f"Failed to save message {doc.id}: {str(e)}")

            # Update history document
            partition_key = user_id or "anonymous"
            try:
                history = history_container.read_item(item=chat_history_id, partition_key=partition_key)
                history["updated_at"] = datetime.utcnow().isoformat()
                history["message_count"] = len(existing_messages) + len(message_docs)
                history_container.upsert_item(history)
            except CosmosResourceNotFoundError:
                # If history doesn't exist, create it
                history_doc = ChatHistoryDocument(
                    chat_history_id=chat_history_id,
                    user_id=user_id or "anonymous",
                    title=f"Chat {chat_history_id[:8]}",
                    message_count=len(message_docs),
                )
                history_doc.id = chat_history_id
                history_container.create_item(body=history_doc.model_dump())

        except Exception as e:
            # Log errors but don't fail the entire operation
            import logging

            logging.error(f"Error saving messages batch: {str(e)}")
            if batch_errors:
                logging.error(f"Batch errors: {batch_errors}")
            raise e

    async def get_chat_history(
        self, chat_history_id: str, user_id: Optional[str] = None
    ) -> Optional[ChatHistoryWithMessages]:
        """Retrieve a chat history with all its messages."""
        history_container = self.client.get_history_container()
        messages_container = self.client.get_messages_container()

        partition_key = user_id or "anonymous"

        try:
            # Get history document
            history_doc = history_container.read_item(item=chat_history_id, partition_key=partition_key)
            history = ChatHistoryDocument(**history_doc)

            # Get all messages for this chat history
            query = """
                    SELECT * \
                    FROM c
                    WHERE c.chat_history_id = @chat_history_id
                    ORDER BY c.sequence \
                    """
            params = [{"name": "@chat_history_id", "value": chat_history_id}]

            messages = []
            for item in messages_container.query_items(
                query=query, parameters=params, enable_cross_partition_query=False
            ):
                messages.append(ChatMessageDocument(**item))

            return ChatHistoryWithMessages(history=history, messages=messages)

        except CosmosResourceNotFoundError:
            return None

    async def list_user_histories(self, user_id: str, limit: int = 20, offset: int = 0) -> List[ChatHistoryDocument]:
        """List chat histories for a user."""
        history_container = self.client.get_history_container()

        query = """
                SELECT * \
                FROM c
                WHERE c.user_id = @user_id
                ORDER BY c.updated_at DESC
                OFFSET @offset LIMIT @limit \
                """
        params = [
            {"name": "@user_id", "value": user_id},
            {"name": "@offset", "value": offset},
            {"name": "@limit", "value": limit},
        ]

        histories = []
        for item in history_container.query_items(query=query, parameters=params, enable_cross_partition_query=False):
            histories.append(ChatHistoryDocument(**item))

        return histories

    async def delete_chat_history(self, chat_history_id: str, user_id: Optional[str] = None) -> bool:
        """Delete a chat history and all its messages."""
        history_container = self.client.get_history_container()
        messages_container = self.client.get_messages_container()

        partition_key = user_id or "anonymous"

        try:
            # Delete all messages first
            query = """
                    SELECT c.id \
                    FROM c
                    WHERE c.chat_history_id = @chat_history_id \
                    """
            params = [{"name": "@chat_history_id", "value": chat_history_id}]

            for item in messages_container.query_items(
                query=query, parameters=params, enable_cross_partition_query=False
            ):
                messages_container.delete_item(item=item["id"], partition_key=chat_history_id)

            # Delete history document
            history_container.delete_item(item=chat_history_id, partition_key=partition_key)

            return True

        except CosmosResourceNotFoundError:
            return False

    async def get_message_count(self, chat_history_id: str) -> int:
        """Get the count of messages for a chat history."""
        messages_container = self.client.get_messages_container()

        query = """
                SELECT VALUE COUNT(1) \
                FROM c
                WHERE c.chat_history_id = @chat_history_id \
                """
        params = [{"name": "@chat_history_id", "value": chat_history_id}]

        result = list(
            messages_container.query_items(query=query, parameters=params, enable_cross_partition_query=False)
        )

        return result[0] if result else 0


# Global repository instance
chat_repository = ChatRepository()
