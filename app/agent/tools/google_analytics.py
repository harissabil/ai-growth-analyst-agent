import json
from datetime import date
from typing import Optional

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from app.clients.google_analytics_client import GoogleAnalyticsClient
from app.config import get_settings
from app.errors.error import APIError


def format_response(data):
    """Serializes Pydantic models to a JSON string for the LLM."""
    try:
        if isinstance(data, list):
            # Handle list of models
            return json.dumps([item.model_dump(mode="json") for item in data], indent=2)
        else:
            # Handle a single model
            return data.model_dump_json(indent=2)
    except Exception as e:
        return f"Error formatting response: {e}"


class TrafficInput(BaseModel):
    start_date: date = Field(..., description="The start date for the report in YYYY-MM-DD format.")
    end_date: date = Field(..., description="The end date for the report in YYYY-MM-DD format.")
    organic_only: bool = Field(False, description="Set to True to get data for organic traffic only.")


class ByDimensionInput(BaseModel):
    start_date: date = Field(..., description="The start date for the report in YYYY-MM-DD format.")
    end_date: date = Field(..., description="The end date for the report in YYYY-MM-DD format.")
    limit: int = Field(10, description="The number of results to return.")
    search: Optional[str] = Field(None, description="A search query to filter results.")


class CountryDetailInput(BaseModel):
    country: str = Field(..., description="The specific country to get data for (e.g., 'spain').")
    start_date: date = Field(..., description="The start date for the report in YYYY-MM-DD format.")
    end_date: date = Field(..., description="The end date for the report in YYYY-MM-DD format.")


class PageDetailInput(BaseModel):
    page_path: str = Field(..., description="The full page path to get data for (e.g., 'vamos.es/todos-los-coches/').")
    start_date: date = Field(..., description="The start date for the report in YYYY-MM-DD format.")
    end_date: date = Field(..., description="The end date for the report in YYYY-MM-DD format.")


@tool(args_schema=TrafficInput)
async def get_google_analytics_overall_traffic(
    start_date: date, end_date: date, organic_only: bool = False, config: RunnableConfig = {}
) -> str:
    """
    Fetches the total, aggregated Google Analytics data (sessions, users, etc.) for a given date range. Use for high-level summaries.

    IMPORTANT: This tool requires specific start_date and end_date. If the user asks a question with a relative date like 'today', 'yesterday', or 'last week', you MUST first use the 'get_current_datetime' tool to determine the exact dates before calling this one.
    """
    try:
        # Return a placeholder response for now
        # return (
        #     '{"sessions": 12345, "users": 6789, "page_views": 101112, "bounce_rate": 50.5, "avg_session_duration": 300}'
        # )
        settings = get_settings()
        token = config.get("configurable", {}).get("auth_token")
        if not token:
            return "Error: Authentication token was not provided to the tool."

        client = GoogleAnalyticsClient(base_url=str(settings.data_service_base_url), token=token)

        data = await client.fetch_overall_data(start_date, end_date, organic_only)
        return format_response(data)
    except APIError as e:
        return f"Error fetching overall traffic: {e.message}"


@tool(args_schema=TrafficInput)
async def get_google_analytics_daily_traffic(
    start_date: date, end_date: date, organic_only: bool = False, config: RunnableConfig = {}
) -> str:
    """
    Fetches a day-by-day breakdown of Google Analytics data for a given date range. Use for trends and daily performance.

    IMPORTANT: This tool requires specific start_date and end_date. If the user asks a question with a relative date like 'today', 'yesterday', or 'last week', you MUST first use the 'get_current_datetime' tool to determine the exact dates before calling this one.
    """
    try:
        # Return a placeholder response for now
        # return '[{"date": "2023-10-01", "sessions": 1000, "users": 800, "page_views": 1500, "bounce_rate": 45.0, "avg_session_duration": 250}, {"date": "2023-10-02", "sessions": 1200, "users": 900, "page_views": 1600, "bounce_rate": 50.0, "avg_session_duration": 300}]'
        settings = get_settings()
        token = config.get("configurable", {}).get("auth_token")
        if not token:
            return "Error: Authentication token was not provided to the tool."
        client = GoogleAnalyticsClient(base_url=str(settings.data_service_base_url), token=token)

        data = await client.fetch_daily_data(start_date, end_date, organic_only)
        return format_response(data)
    except APIError as e:
        return f"Error fetching daily traffic: {e.message}"


@tool(args_schema=ByDimensionInput)
async def get_google_analytics_traffic_by_countries(
    start_date: date,
    end_date: date,
    limit: int = 10,
    search: Optional[str] = None,
    config: RunnableConfig = {},
) -> str:
    """
    Fetches a list of countries ranked by traffic metrics for a given date range from Google Analytics.

    IMPORTANT: This tool requires specific start_date and end_date. If the user asks a question with a relative date like 'today', 'yesterday', or 'last week', you MUST first use the 'get_current_datetime' tool to determine the exact dates before calling this one.
    """
    try:
        # Return a placeholder response for now
        # return '[{"country": "United States", "sessions": 5000, "users": 4000, "page_views": 7000, "bounce_rate": 40.0, "avg_session_duration": 320}, {"country": "Spain", "sessions": 3000, "users": 2500, "page_views": 4500, "bounce_rate": 50.0, "avg_session_duration": 280}]'
        settings = get_settings()
        token = config.get("configurable", {}).get("auth_token")
        if not token:
            return "Error: Authentication token was not provided to the tool."
        client = GoogleAnalyticsClient(base_url=str(settings.data_service_base_url), token=token)

        data = await client.fetch_countries_data(start_date, end_date, limit=limit, search=search)
        return format_response(data)
    except APIError as e:
        return f"Error fetching traffic by country: {e.message}"


@tool(args_schema=CountryDetailInput)
async def get_google_analytics_daily_traffic_for_country(
    country: str, start_date: date, end_date: date, config: RunnableConfig = {}
) -> str:
    """
    Fetches a day-by-day traffic breakdown for a single, specific country from Google Analytics.

    IMPORTANT: This tool requires specific start_date and end_date. If the user asks a question with a relative date like 'today', 'yesterday', or 'last week', you MUST first use the 'get_current_datetime' tool to determine the exact dates before calling this one.
    """
    try:
        # Return a placeholder response for now
        # return '[{"date": "2023-10-01", "sessions": 800, "users": 600, "page_views": 900, "bounce_rate": 42.0, "avg_session_duration": 290}, {"date": "2023-10-02", "sessions": 900, "users": 700, "page_views": 1000, "bounce_rate": 48.0, "avg_session_duration": 310}]'
        settings = get_settings()
        token = config.get("configurable", {}).get("auth_token")
        if not token:
            return "Error: Authentication token was not provided to the tool."
        client = GoogleAnalyticsClient(base_url=str(settings.data_service_base_url), token=token)

        data = await client.fetch_country_detail_data(country, start_date, end_date)
        return format_response(data)
    except APIError as e:
        return f"Error fetching traffic for {country}: {e.message}"


@tool(args_schema=ByDimensionInput)
async def get_google_analytics_traffic_by_pages(
    start_date: date,
    end_date: date,
    limit: int = 10,
    search: Optional[str] = None,
    config: RunnableConfig = {},
) -> str:
    """
    Fetches a list of website pages ranked by traffic metrics for a given date range from Google Analytics.

    IMPORTANT: This tool requires specific start_date and end_date. If the user asks a question with a relative date like 'today', 'yesterday', or 'last week', you MUST first use the 'get_current_datetime' tool to determine the exact dates before calling this one.
    """
    try:
        # Return a placeholder response for now
        # return '[{"page_path": "/home", "sessions": 4000, "users": 3500, "page_views": 6000, "bounce_rate": 38.0, "avg_session_duration": 330}, {"page_path": "/products", "sessions": 2500, "users": 2000, "page_views": 3000, "bounce_rate": 45.0, "avg_session_duration": 290}]'
        settings = get_settings()
        token = config.get("configurable", {}).get("auth_token")
        if not token:
            return "Error: Authentication token was not provided to the tool."
        client = GoogleAnalyticsClient(base_url=str(settings.data_service_base_url), token=token)

        data = await client.fetch_pages_data(start_date, end_date, limit=limit, search=search)
        return format_response(data)
    except APIError as e:
        return f"Error fetching traffic by page: {e.message}"


@tool(args_schema=PageDetailInput)
async def get_google_analytics_daily_traffic_for_page(
    page_path: str, start_date: date, end_date: date, config: RunnableConfig = {}
) -> str:
    """
    Fetches a day-by-day traffic breakdown for a single, specific page path from Google Analytics.

    IMPORTANT: This tool requires specific start_date and end_date. If the user asks a question with a relative date like 'today', 'yesterday', or 'last week', you MUST first use the 'get_current_datetime' tool to determine the exact dates before calling this one.
    """
    try:
        # Return a placeholder response for now
        # return '[{"date": "2023-10-01", "sessions": 600, "users": 500, "page_views": 700, "bounce_rate": 44.0, "avg_session_duration": 270}, {"date": "2023-10-02", "sessions": 700, "users": 600, "page_views": 800, "bounce_rate": 46.0, "avg_session_duration": 290}]'
        settings = get_settings()
        token = config.get("configurable", {}).get("auth_token")
        if not token:
            return "Error: Authentication token was not provided to the tool."
        client = GoogleAnalyticsClient(base_url=str(settings.data_service_base_url), token=token)

        data = await client.fetch_page_detail_data(page_path, start_date, end_date)
        return format_response(data)
    except APIError as e:
        return f"Error fetching traffic for page {page_path}: {e.message}"
