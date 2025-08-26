from fastapi import APIRouter
from pydantic import BaseModel

from app.agent.agent import get_graph
from app.utils.chat_utils import convert_message

router = APIRouter()
graph = get_graph()


class ChatTurn(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatTurn]


class ChatResponse(BaseModel):
    messages: list[ChatTurn]


@router.post("/", response_model=ChatResponse)
async def chat_with_agent(request: ChatRequest):
    state = {"messages": [m.model_dump() for m in request.messages]}
    result = graph.invoke(state)
    return {
        "messages": [convert_message(m) for m in result["messages"]]
    }
