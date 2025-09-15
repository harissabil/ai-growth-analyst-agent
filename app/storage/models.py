from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.storage.db import Base


def guid() -> str:
    return str(uuid.uuid4())


class ChatHistory(Base):
    __tablename__ = "chat_history"

    chat_history_id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=guid)
    user_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), server_default=text("CURRENT_TIMESTAMP"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), server_default=text("CURRENT_TIMESTAMP"))

    messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="history", cascade="all, delete-orphan", order_by="ChatMessage.sequence"
    )


# Composite index (user_id, created_at)
Index("ix_chat_history_user_created", ChatHistory.user_id, ChatHistory.created_at)


class ChatMessage(Base):
    __tablename__ = "chat_message"

    chat_message_id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=guid)
    chat_history_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("chat_history.chat_history_id", ondelete="CASCADE"),
        index=True,
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=False), server_default=text("CURRENT_TIMESTAMP"))

    role: Mapped[str] = mapped_column(String(16), nullable=False)  # user|assistant|system|tool
    message: Mapped[str] = mapped_column(Text, nullable=False)
    tables: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    history: Mapped[ChatHistory] = relationship(back_populates="messages")


# Composite index (chat_history_id, sequence)
Index("ix_chat_message_history", ChatMessage.chat_history_id, ChatMessage.sequence)
