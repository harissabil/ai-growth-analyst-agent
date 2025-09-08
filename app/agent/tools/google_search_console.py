import json
from datetime import date
from typing import Optional

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from app.clients.google_search_console_client import GoogleSearchConsoleClient
from app.config import get_settings
from app.errors.error import APIError


def format_response(data):
    """Serializes Pydantic models to a JSON string for the LLM."""
    try:
        if isinstance(data, list):
            return json.dumps([item.model_dump(mode="json") for item in data], indent=2)
        else:
            return data.model_dump_json(indent=2)
    except Exception as e:
        return f"Error formatting response: {e}"


# Schemas
class GscTrafficInput(BaseModel):
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


class GscByDimensionInput(BaseModel):
    start_date: date = Field(
        ...,
        description="Start date in YYYY-MM-DD (resolve relative dates first).",
    )
    end_date: date = Field(
        ...,
        description="End date in YYYY-MM-DD (resolve relative dates first).",
    )
    limit: int = Field(
        10,
        description="Max rows to return (maps from 'top N' or 'list N'). Sane range: 1–50; default 10.",
    )
    search: Optional[str] = Field(
        None,
        description=(
            "Case-insensitive contains filter. "
            "For keywords: filters by query term substring. "
            "For countries: filters by country name substring (e.g., 'es' matches 'Spain', 'United States')."
        ),
    )


class GscCountryDetailInput(BaseModel):
    country: str = Field(
        ...,
        description=(
            "Country path param. Service allows partial but it must uniquely identify a country "
            "(e.g., 'spain' or a unique substring per service rules)."
        ),
    )
    start_date: date = Field(..., description="Start date in YYYY-MM-DD (resolve relative dates first).")
    end_date: date = Field(..., description="End date in YYYY-MM-DD (resolve relative dates first).")


class GscKeywordDetailInput(BaseModel):
    keyword: str = Field(
        ...,
        description=(
            "Exact keyword (query) for the path param. Must match the service's keyword exactly; "
            "URL encoding is handled by the HTTP client."
        ),
    )
    start_date: date = Field(..., description="Start date in YYYY-MM-DD (resolve relative dates first).")
    end_date: date = Field(..., description="End date in YYYY-MM-DD (resolve relative dates first).")


# Tools
@tool(args_schema=GscTrafficInput)
async def get_search_console_overall(start_date: date, end_date: date, config: RunnableConfig = {}) -> str:
    """
    Source: Google Search Console
    Purpose: High-level totals (clicks, impressions, ctr_percent, average_position) for a date range.
    Required: start_date, end_date (absolute dates).
    """
    try:
        settings = get_settings()
        token = config.get("configurable", {}).get("auth_token")
        if not token:
            return "Error: Authentication token was not provided to the tool."

        client = GoogleSearchConsoleClient(base_url=str(settings.data_service_base_url), token=token)
        data = await client.fetch_overall_data(start_date, end_date)
        return format_response(data)
    except APIError as e:
        return f"Error fetching Search Console overall: {e.errors}"


@tool(args_schema=GscTrafficInput)
async def get_search_console_daily(start_date: date, end_date: date, config: RunnableConfig = {}) -> str:
    """
    Source: Google Search Console
    Purpose: Daily time series of clicks/impressions/ctr_percent/average_position.
    Required: start_date, end_date (absolute dates).
    """
    try:
        settings = get_settings()
        token = config.get("configurable", {}).get("auth_token")
        if not token:
            return "Error: Authentication token was not provided to the tool."

        client = GoogleSearchConsoleClient(base_url=str(settings.data_service_base_url), token=token)
        data = await client.fetch_daily_data(start_date, end_date)
        return format_response(data)
    except APIError as e:
        return f"Error fetching Search Console daily: {e.errors}"


@tool(args_schema=GscByDimensionInput)
async def get_search_console_keywords(
    start_date: date,
    end_date: date,
    limit: int = 10,
    search: Optional[str] = None,
    config: RunnableConfig = {},
) -> str:
    """
    Source: Google Search Console
    Purpose: Rank search queries (keywords) by clicks/impressions for a date range.
    Mapping: 'top N' → limit=N; 'filter by <term>' → search='<term>' (case-insensitive contains).
    Required: start_date, end_date (absolute). Optional: limit (default 10), search.
    """
    try:
        settings = get_settings()
        token = config.get("configurable", {}).get("auth_token")
        if not token:
            return "Error: Authentication token was not provided to the tool."

        client = GoogleSearchConsoleClient(base_url=str(settings.data_service_base_url), token=token)
        data = await client.fetch_keywords_data(start_date, end_date, limit=limit, search=search)
        return format_response(data)
    except APIError as e:
        return f"Error fetching Search Console keywords: {e.errors}"


@tool(args_schema=GscKeywordDetailInput)
async def get_search_console_daily_for_keyword(
    keyword: str, start_date: date, end_date: date, config: RunnableConfig = {}
) -> str:
    """
    Source: Google Search Console
    Purpose: Daily breakdown for a single exact keyword over a date range.
    Required: keyword (exact), start_date, end_date (absolute).
    """
    try:
        settings = get_settings()
        token = config.get("configurable", {}).get("auth_token")
        if not token:
            return "Error: Authentication token was not provided to the tool."

        client = GoogleSearchConsoleClient(base_url=str(settings.data_service_base_url), token=token)
        data = await client.fetch_keyword_detail_data(keyword, start_date, end_date)
        return format_response(data)
    except APIError as e:
        return f"Error fetching Search Console for keyword '{keyword}': {e.errors}"


@tool(args_schema=GscByDimensionInput)
async def get_search_console_countries(
    start_date: date,
    end_date: date,
    limit: int = 10,
    search: Optional[str] = None,
    config: RunnableConfig = {},
) -> str:
    """
    Source: Google Search Console
    Purpose: Rank countries by clicks/impressions/ctr_percent/average_position.
    Mapping: 'top N' → limit=N; filter by substring → search (case-insensitive contains).
    Required: start_date, end_date (absolute). Optional: limit (default 10), search.
    """
    try:
        settings = get_settings()
        token = config.get("configurable", {}).get("auth_token")
        if not token:
            return "Error: Authentication token was not provided to the tool."

        client = GoogleSearchConsoleClient(base_url=str(settings.data_service_base_url), token=token)
        data = await client.fetch_countries_data(start_date, end_date, limit=limit, search=search)
        return format_response(data)
    except APIError as e:
        return f"Error fetching Search Console countries: {e.errors}"


@tool(args_schema=GscCountryDetailInput)
async def get_search_console_daily_for_country(
    country: str, start_date: date, end_date: date, config: RunnableConfig = {}
) -> str:
    """
    Source: Google Search Console
    Purpose: Daily breakdown for a single country over a date range.
    Note: The path can be a unique partial per service rules (e.g., 'spain').
    Required: country, start_date, end_date (absolute).
    """
    try:
        settings = get_settings()
        token = config.get("configurable", {}).get("auth_token")
        if not token:
            return "Error: Authentication token was not provided to the tool."

        client = GoogleSearchConsoleClient(base_url=str(settings.data_service_base_url), token=token)
        data = await client.fetch_country_detail_data(country, start_date, end_date)
        return format_response(data)
    except APIError as e:
        return f"Error fetching Search Console for country '{country}': {e.errors}"
