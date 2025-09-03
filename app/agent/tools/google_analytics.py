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
    start_date: date = Field(
        ...,
        description=(
            "Start date in YYYY-MM-DD. Must be <= end_date. "
            "If the user used a relative date, resolve to an absolute date via get_current_datetime first."
        ),
    )
    end_date: date = Field(
        ...,
        description=(
            "End date in YYYY-MM-DD. Must be >= start_date. "
            "If the user used a relative date, resolve via get_current_datetime first."
        ),
    )
    organic_only: bool = Field(
        False,
        description=(
            "Set True to restrict to organic traffic only (maps from phrases like 'organic only')."
        ),
    )


class ByDimensionInput(BaseModel):
    start_date: date = Field(
        ...,
        description=(
            "Start date in YYYY-MM-DD. Resolve relative dates (today/yesterday/last week/month/quarter) via get_current_datetime first."
        ),
    )
    end_date: date = Field(
        ...,
        description=(
            "End date in YYYY-MM-DD. Resolve relative dates via get_current_datetime first."
        ),
    )
    limit: int = Field(
        10,
        description=(
            "Max rows to return (maps from 'top N' or 'list N'). "
            "Sane range: 1–50; defaults to 10 if unspecified."
        ),
    )
    search: Optional[str] = Field(
        None,
        description=(
            "Keyword filter (case-insensitive 'contains'). "
            "For pages: applies to page path/title as supported by backend. "
            "For countries: applies to country name or keyword that includes in the name (e.g., 'United' matches 'United States', 'Spain'). "
            "Maps from user keywords like 'BMW'."
        ),
    )


class CountryDetailInput(BaseModel):
    country: str = Field(
        ...,
        description=(
            "The specific country to get data for (e.g., 'spain')."
        ),
    )
    start_date: date = Field(
        ...,
        description="Start date in YYYY-MM-DD (resolve relative dates first).",
    )
    end_date: date = Field(
        ...,
        description="End date in YYYY-MM-DD (resolve relative dates first).",
    )


class PageDetailInput(BaseModel):
    page_path: str = Field(
        ...,
        description=(
            "The page path without dns name to get data for (e.g., '/home' or '/renting-bmw-x8/details')."
        ),
    )
    start_date: date = Field(
        ...,
        description="Start date in YYYY-MM-DD (resolve relative dates first).",
    )
    end_date: date = Field(
        ...,
        description="End date in YYYY-MM-DD (resolve relative dates first).",
    )


@tool(args_schema=TrafficInput)
async def get_google_analytics_overall_traffic(
        start_date: date, end_date: date, organic_only: bool = False, config: RunnableConfig = {}
) -> str:
    """
    Source: Google Analytics
    Purpose: High-level totals/trends (sessions, users, etc.) for a date range.
    When to use: The user asks for overall/aggregate metrics across a period.
    Required: start_date, end_date (must be absolute; resolve relative dates via get_current_datetime first).
    Options: organic_only=True if user requests 'organic only'.
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
    Source: Google Analytics
    Purpose: Daily time series for a date range (trend analysis).
    Required: start_date, end_date (absolute dates).
    Options: organic_only=True if requested.
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
    Source: Google Analytics
    Purpose: Rank countries by traffic metrics for a date range.
    Mapping: 'top N' → limit=N; 'the country with the es included in its name' → search='es'.
    Required: start_date, end_date (absolute).
    Optional: limit (default 10), search (case-insensitive 'contains').
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
    Source: Google Analytics
    Purpose: Daily breakdown for a single country over a date range.
    Required: country, start_date, end_date (absolute).
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
    Source: Google Analytics
    Purpose: Rank pages by traffic metrics for a date range.
    Mapping: 'top N' → limit=N; user keywords (e.g., 'BMW') → search='BMW' (case-insensitive contains).
    Required: start_date, end_date (absolute).
    Optional: limit (default 10), search (optional, if not provided, return top N overall).
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
    Source: Google Analytics
    Purpose: Daily breakdown for a single page over a date range.
    Required: page_path, start_date, end_date (absolute).
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
