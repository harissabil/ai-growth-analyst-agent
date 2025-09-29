import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.agent.agent import get_graph
from app.agent.tools.table.table_attach import attach_tables_to_assistant_turns
from app.logging import AuditJSONHandler
from app.schemas.request import ChatRequest
from app.schemas.response import ChatResponse, ChatTurn, TableSpec
from app.storage.cosmos_chat_repo import chat_repository
from app.utils.auth_utils import verify_token_and_get_user_id
from app.utils.chat_utils import is_public, to_public_messages

router = APIRouter()
graph = get_graph()


@router.post("", response_model=ChatResponse)
async def chat_with_agent(
    request: ChatRequest,
    chat_history_id: Optional[str] = Query(default=None),
    auth_data: tuple = Depends(verify_token_and_get_user_id),
):
    """Process a chat request through the AI agent."""
    # Extract token and user_id from auth dependency
    token, user_id = auth_data

    try:
        # 1) Ensure a chat history row
        first_user_text = next((m.content for m in request.messages if m.role == "user"), None) or "New chat"

        history_id = await chat_repository.ensure_history(chat_history_id, user_id, first_user_text)

        # 2) Build graph state + config
        state = {"messages": [m.model_dump() for m in request.messages]}

        corr_id = str(uuid.uuid4())
        callbacks = [AuditJSONHandler(corr_id)]
        for cb in callbacks:
            if hasattr(cb, "logger"):
                cb.logger = cb.logger

        config = {
            "configurable": {"auth_token": token},
            "callbacks": callbacks,
            "metadata": {"correlation_id": corr_id},
        }

        # 3) Run agent
        result = await graph.ainvoke(state, config=config)
        full_messages = result.get("messages") or []

        # Safety: bail early with a well-formed response if nothing came back
        if not full_messages:
            await chat_repository.save_messages_batch(history_id, [], {}, user_id)
            return ChatResponse(
                chat_history_id=history_id,
                messages=[
                    ChatTurn(role="assistant", content="I didn't receive any messages from the agent.", tables=None)
                ],
            )

        # 4) Build table mapping from tool outputs (keyed by index in full_messages)
        tables_by_assistant_idx = attach_tables_to_assistant_turns(full_messages)

        # 5) Determine the order of PUBLIC assistant messages by their indices in full_messages
        assistant_public_full_idxs = [
            i
            for i, m in enumerate(full_messages)
            if is_public(m)
            and (getattr(m, "type", None) in ("ai", "assistant") or getattr(m, "role", None) == "assistant")
        ]

        # 6) For each public assistant, pick its tables by the full index
        assistant_tables_iter: List[List[TableSpec]] = [
            tables_by_assistant_idx.get(i) or [] for i in assistant_public_full_idxs
        ]

        # 7) Convert to public messages and attach tables aligned with the public assistant order
        public = to_public_messages(full_messages)

        out_messages: List[ChatTurn] = []
        assistant_seen = 0
        for pm in public:
            role = pm.get("role")
            content = pm.get("content", "")
            if role == "assistant":
                tables = assistant_tables_iter[assistant_seen] if assistant_seen < len(assistant_tables_iter) else []
                assistant_seen += 1
                out_messages.append(ChatTurn(role="assistant", content=content, tables=tables or None))
            else:
                out_messages.append(ChatTurn(role=role, content=content))

        # 8) Persist full timeline (and per-assistant tables mapping)
        await chat_repository.save_messages_batch(history_id, full_messages, tables_by_assistant_idx, user_id)

        # 9) Return response
        return ChatResponse(chat_history_id=history_id, messages=out_messages)

    except Exception as e:
        # Log the error appropriately
        import logging

        logging.error(f"Error in chat endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error during chat processing")


@router.get("/history/{chat_history_id}", response_model=ChatResponse)
async def get_chat_history(
    chat_history_id: str,
    auth_data: tuple = Depends(verify_token_and_get_user_id),
):
    """Retrieve a specific chat history with all messages."""
    # Extract token and user_id from auth dependency
    token, user_id = auth_data

    history_with_messages = await chat_repository.get_chat_history(chat_history_id, user_id)

    if not history_with_messages:
        raise HTTPException(status_code=404, detail="Chat history not found")

    # Convert to response format
    messages = []
    for msg in history_with_messages.messages:
        # Skip tool messages when retrieving from database (they shouldn't be in public response)
        if msg.role == "tool":
            continue

        turn = ChatTurn(
            role=msg.role, content=msg.message, tables=[TableSpec(**t) for t in msg.tables] if msg.tables else None
        )
        messages.append(turn)

    return ChatResponse(chat_history_id=chat_history_id, messages=messages)


@router.get("/histories", response_model=List[dict])
async def list_user_histories(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    auth_data: tuple = Depends(verify_token_and_get_user_id),
):
    """List chat histories for a user."""
    # Extract token and user_id from auth dependency
    token, user_id = auth_data

    histories = await chat_repository.list_user_histories(user_id, limit, offset)

    return [
        {
            "chat_history_id": h.chat_history_id,
            "title": h.title,
            "created_at": h.created_at,
            "updated_at": h.updated_at,
            "message_count": h.message_count,
        }
        for h in histories
    ]


@router.delete("/history/{chat_history_id}")
async def delete_chat_history(
    chat_history_id: str,
    auth_data: tuple = Depends(verify_token_and_get_user_id),
):
    """Delete a chat history and all its messages."""
    # Extract token and user_id from auth dependency
    token, user_id = auth_data

    success = await chat_repository.delete_chat_history(chat_history_id, user_id)

    if not success:
        raise HTTPException(status_code=404, detail="Chat history not found")

    return {"message": "Chat history deleted successfully"}
