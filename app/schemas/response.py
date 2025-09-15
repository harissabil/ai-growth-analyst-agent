from pydantic import BaseModel
from typing import List, Literal, Any, Optional

class TableSpec(BaseModel):
    name: str
    columns: List[str]
    rows: List[List[Any]]

class ChatTurn(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str
    tables: Optional[List[TableSpec]] = None

class ChatResponse(BaseModel):
    chat_history_id: str
    messages: List[ChatTurn]
