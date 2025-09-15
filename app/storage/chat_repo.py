from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import func, select, update

from app.storage.db import SessionLocal
from app.storage.models import ChatHistory, ChatMessage


def _derive_title(text: str, max_len: int = 60) -> str:
    t = " ".join(text.strip().split())
    return t[:max_len] + ("…" if len(t) > max_len else "")


def ensure_history(chat_history_id: Optional[str], user_id: Optional[str], title_hint: str) -> str:
    with SessionLocal() as s:
        if chat_history_id:
            s.execute(
                update(ChatHistory)
                .where(ChatHistory.chat_history_id == chat_history_id)
                .values(updated_at=datetime.utcnow())
            )
            s.commit()
            return chat_history_id
        h = ChatHistory(user_id=user_id, title=_derive_title(title_hint))
        s.add(h)
        s.flush()  # assign PK
        s.commit()
        return h.chat_history_id


def save_messages_batch(
    chat_history_id: str,
    messages: List[Any],
    tables_by_assistant_idx: Dict[int, List[Any]],
):
    with SessionLocal() as s:
        # starting sequence
        current_max = s.execute(
            select(func.max(ChatMessage.sequence)).where(ChatMessage.chat_history_id == chat_history_id)
        ).scalar()
        seq = (current_max or 0) + 1

        db_rows_by_full_idx: Dict[int, ChatMessage] = {}

        for i, m in enumerate(messages):
            role = getattr(m, "type", None) or getattr(m, "role", None) or m.__class__.__name__.lower()
            if role in ("ai", "assistant"):
                role = "assistant"
            elif role in ("human", "user"):
                role = "user"
            elif role in ("tool",):
                role = "tool"
            elif role in ("system",):
                role = "system"
            else:
                role = "assistant" if "AIMessage" in str(type(m)) else "user"

            content = getattr(m, "content", "")
            row = ChatMessage(
                chat_history_id=chat_history_id,
                sequence=seq,
                role=role,
                message=content if isinstance(content, str) else str(content),
                tables=None,
            )
            s.add(row)
            db_rows_by_full_idx[i] = row
            seq += 1

        s.flush()

        # attach per-assistant tables
        for assistant_idx, tables in tables_by_assistant_idx.items():
            row = db_rows_by_full_idx.get(assistant_idx)
            if row and row.role == "assistant" and tables:
                row.tables = [t.model_dump() for t in tables]

        s.execute(
            update(ChatHistory)
            .where(ChatHistory.chat_history_id == chat_history_id)
            .values(updated_at=datetime.utcnow())
        )
        s.commit()
