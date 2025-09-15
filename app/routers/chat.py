import uuid
from typing import List, Optional

from fastapi import APIRouter, Query, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.concurrency import run_in_threadpool

from app.agent.agent import get_graph
from app.agent.tools.table.table_attach import attach_tables_to_assistant_turns
from app.logging import AuditJSONHandler
from app.schemas.request import ChatRequest
from app.schemas.response import ChatResponse, ChatTurn, TableSpec
from app.storage.chat_repo import ensure_history, save_messages_batch
from app.utils.chat_utils import to_public_messages

bearer_scheme = HTTPBearer(scheme_name="Bearer", description="Enter your Bearer token", bearerFormat="JWT")

router = APIRouter()
graph = get_graph()


@router.post("", response_model=ChatResponse)
async def chat_with_agent(
    request: ChatRequest,
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
    chat_history_id: Optional[str] = Query(default=None),
    user_id: Optional[str] = Query(default=None),
):
    token = credentials.credentials

    # 1) Ensure a chat history row
    first_user_text = next((m.content for m in request.messages if m.role == "user"), None) or "New chat"
    history_id = await run_in_threadpool(lambda: ensure_history(chat_history_id, user_id, first_user_text))

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
        await run_in_threadpool(lambda: save_messages_batch(history_id, [], {}))
        return {
            "chat_history_id": history_id,
            "messages": [
                {"role": "assistant", "content": "I didn’t receive any messages from the agent.", "tables": None}
            ],
        }

    # 4) Build table mapping from tool outputs (keyed by index in full_messages)
    tables_by_assistant_idx = attach_tables_to_assistant_turns(full_messages)

    # 5) Determine the order of PUBLIC assistant messages by their indices in full_messages
    from app.utils.chat_utils import is_public  # local import avoids circulars in some setups

    assistant_public_full_idxs = [
        i
        for i, m in enumerate(full_messages)
        if is_public(m) and (getattr(m, "type", None) in ("ai", "assistant") or getattr(m, "role", None) == "assistant")
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
    await run_in_threadpool(lambda: save_messages_batch(history_id, full_messages, tables_by_assistant_idx))

    # 9) Return a plain dict (FastAPI will coerce to ChatResponse)
    return {
        "chat_history_id": history_id,
        "messages": [m.model_dump(exclude_none=True) for m in out_messages],
    }
