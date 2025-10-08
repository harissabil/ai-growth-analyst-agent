import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


def generate_id() -> str:
    """Generate a new UUID for document IDs."""
    return str(uuid.uuid4())


def utcnow() -> str:
    """Get current UTC timestamp as ISO string."""
    return datetime.utcnow().isoformat()


class ChatHistoryDocument(BaseModel):
    """Document model for chat history in Cosmos DB."""

    id: str = Field(default_factory=generate_id)  # Cosmos DB requires 'id' field
    chat_history_id: str = Field(default_factory=generate_id)
    user_id: Optional[str] = Field(default=None)
    title: str = Field(max_length=200)
    created_at: str = Field(default_factory=utcnow)
    updated_at: str = Field(default_factory=utcnow)
    message_count: int = Field(default=0)  # Denormalized counter for optimization

    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "chat_history_id": "123e4567-e89b-12d3-a456-426614174000",
                "user_id": "user123",
                "title": "Chat about AI development",
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00",
                "message_count": 0,
            }
        }

    @field_validator("id", mode="before")
    @classmethod
    def set_id_from_chat_history_id(cls, v, info):
        """Ensure id matches chat_history_id for consistency."""
        if not v and info.data and "chat_history_id" in info.data:
            return info.data["chat_history_id"]
        return v or generate_id()


class ChatMessageDocument(BaseModel):
    """Document model for chat messages in Cosmos DB."""

    id: str = Field(default_factory=generate_id)
    chat_message_id: str = Field(default_factory=generate_id)
    chat_history_id: str  # Partition key
    sequence: int
    timestamp: str = Field(default_factory=utcnow)
    role: str = Field(max_length=16)  # user|assistant|system|tool
    message: str
    tables: Optional[List[Dict[str, Any]]] = None

    # Additional metadata for optimization
    message_preview: Optional[str] = None  # First 100 chars for quick display

    class Config:
        json_schema_extra = {
            "example": {
                "id": "msg-123e4567",
                "chat_message_id": "msg-123e4567",
                "chat_history_id": "123e4567-e89b-12d3-a456-426614174000",
                "sequence": 1,
                "timestamp": "2024-01-01T00:00:00",
                "role": "user",
                "message": "Hello, AI assistant!",
                "tables": None,
                "message_preview": "Hello, AI assistant!",
            }
        }

    @field_validator("message_preview", mode="before")
    @classmethod
    def set_message_preview(cls, v, info):
        """Auto-generate message preview if not provided."""
        if not v and info.data and "message" in info.data:
            message = info.data["message"]
            return message[:100] + "..." if len(message) > 100 else message
        return v

    @field_validator("id", mode="before")
    @classmethod
    def set_id_from_chat_message_id(cls, v, info):
        """Ensure id matches chat_message_id for consistency."""
        if not v and info.data and "chat_message_id" in info.data:
            return info.data["chat_message_id"]
        return v or generate_id()


class ChatHistoryWithMessages(BaseModel):
    """Composite model for chat history with messages."""

    history: ChatHistoryDocument
    messages: List[ChatMessageDocument] = Field(default_factory=list)

    class Config:
        json_schema_extra = {
            "example": {
                "history": ChatHistoryDocument.Config.json_schema_extra["example"],
                "messages": [ChatMessageDocument.Config.json_schema_extra["example"]],
            }
        }
