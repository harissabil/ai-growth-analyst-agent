from typing import Iterable

from langchain.schema import AIMessage, HumanMessage, SystemMessage
from langchain_core.messages import BaseMessage, ToolMessage


def convert_message(msg: BaseMessage) -> dict:
    if isinstance(msg, HumanMessage):
        return {"role": "user", "content": msg.content}
    elif isinstance(msg, AIMessage):
        return {"role": "assistant", "content": msg.content}
    elif isinstance(msg, SystemMessage):
        return {"role": "system", "content": msg.content}
    else:
        raise ValueError(f"Unsupported message type: {type(msg)}")


def is_public(msg: BaseMessage) -> bool:
    # Hide tool plumbing:
    # - Any ToolMessage
    # - Any AIMessage that only carries tool_calls and has empty content
    if isinstance(msg, ToolMessage):
        return False
    if isinstance(msg, AIMessage) and not msg.content and getattr(msg, "tool_calls", None):
        return False
    return isinstance(msg, (HumanMessage, AIMessage, SystemMessage))


def to_public_messages(messages: Iterable[BaseMessage]) -> list[dict]:
    return [convert_message(m) for m in messages if is_public(m)]
