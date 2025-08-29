from datetime import datetime

from langchain_core.tools import tool


@tool
def get_current_datetime() -> str:
    """Returns the current date and time in ISO 8601 format. Use this to know the current time or today's date."""
    return datetime.now().isoformat()
