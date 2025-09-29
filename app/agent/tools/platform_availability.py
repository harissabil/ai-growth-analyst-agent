import json

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from app.clients.platform_client import platform_client
from app.errors.error import APIError


def format_response(data):
    """Serializes platform data to a JSON string for the LLM."""
    try:
        if isinstance(data, dict):
            return json.dumps(data, indent=2)
        else:
            return str(data)
    except Exception as e:
        return f"Error formatting response: {e}"


@tool
async def check_platform_availability(config: RunnableConfig = {}) -> str:
    """
    Source: Platform Service
    Purpose: Check which platforms (Google Analytics, Search Console, Google Ads) are connected and available.
    When to use: Before attempting to fetch data from any platform to ensure the platform is properly connected.
    Returns: Connection status and current configuration for each platform.

    This tool should be called first before using any GA4, GSC, or Google Ads tools.
    """
    try:
        token = config.get("configurable", {}).get("auth_token")
        if not token:
            return "Error: Authentication token was not provided to the tool."

        platform_response = await platform_client.get_platform(token)

        # Extract the relevant information for the AI
        result = {
            "google_analytics": {
                "connected": platform_response.data.google_analytics.connected,
                "current": platform_response.data.google_analytics.current.model_dump()
                if platform_response.data.google_analytics.current
                else None,
            },
            "google_search_console": {
                "connected": platform_response.data.google_search_console.connected,
                "current": platform_response.data.google_search_console.current.model_dump()
                if platform_response.data.google_search_console.current
                else None,
            },
            "google_ads": {
                "connected": platform_response.data.google_ads.connected,
                "current": platform_response.data.google_ads.current.model_dump()
                if platform_response.data.google_ads.current
                else None,
            },
        }

        return format_response(result)

    except APIError as e:
        return f"Error checking platform availability: {e.errors}"
    except Exception as e:
        return f"Error checking platform availability: {str(e)}"
