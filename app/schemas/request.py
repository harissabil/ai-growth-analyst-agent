from pydantic import BaseModel

from app.schemas.response import ChatTurn


class ChatRequest(BaseModel):
    messages: list[ChatTurn]
