import uuid

from fastapi import APIRouter, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from app.agent.agent import get_graph
from app.logging import AuditJSONHandler
from app.utils.chat_utils import to_public_messages

bearer_scheme = HTTPBearer(
    scheme_name="Bearer", description="Enter your Bearer token", bearerFormat="JWT"
)

router = APIRouter()
graph = get_graph()


class ChatTurn(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatTurn]


class ChatResponse(BaseModel):
    messages: list[ChatTurn]


@router.post("", response_model=ChatResponse)
async def chat_with_agent(
    request: ChatRequest,
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
):
    token = credentials.credentials
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

    result = await graph.ainvoke(state, config=config)
    return {"messages": to_public_messages(result["messages"])}
