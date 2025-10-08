from typing import Any, Dict, List, Optional

from app.agent.tools.table.table_builders import TOOL_TABLE_BUILDERS
from app.schemas.response import TableSpec


def _build_tables_for_tool(tool_name: Optional[str], content: str) -> List[TableSpec]:
    if not tool_name or not isinstance(content, str):
        return []
    if content.strip().lower().startswith("error:"):
        return []
    builder = TOOL_TABLE_BUILDERS.get(tool_name)
    return builder(content) if builder else []


def attach_tables_to_assistant_turns(messages: List[Any]) -> Dict[int, List[TableSpec]]:
    """
    Returns a mapping: assistant_message_index_in_full_messages -> [TableSpec,...]
    We accumulate tables from tool messages until we hit the next assistant AIMessage.
    """
    pending: List[TableSpec] = []
    mapping: Dict[int, List[TableSpec]] = {}
    for idx, m in enumerate(messages):
        typ = getattr(m, "type", None) or getattr(m, "role", None) or m.__class__.__name__.lower()
        if typ == "tool":
            tool_name = getattr(m, "name", None)
            content = getattr(m, "content", "")
            pending.extend(_build_tables_for_tool(tool_name, content))
        elif typ in ("ai", "assistant"):
            if pending:
                mapping[idx] = pending
                pending = []
    return mapping
