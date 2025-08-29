from fastapi import APIRouter, Depends, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from app.agent.agent import get_graph
from app.utils.chat_utils import convert_message

bearer_scheme = HTTPBearer(
    scheme_name="Bearer", description="Enter your Bearer token", bearerFormat="JWT"
)

router = APIRouter(dependencies=[Depends(bearer_scheme)])
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
    config = {"configurable": {"auth_token": token}}
    result = await graph.ainvoke(state, config=config)
    return {"messages": [convert_message(m) for m in result["messages"]]}
