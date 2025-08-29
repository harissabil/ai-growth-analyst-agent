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
    organic_only: bool = Field(
        False, description="Set to True to get data for organic traffic only."
    )


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
    page_path: str = Field(
        ..., description="The full page path to get data for (e.g., 'vamos.es/todos-los-coches/')."
    )
    start_date: date = Field(..., description="The start date for the report in YYYY-MM-DD format.")
    end_date: date = Field(..., description="The end date for the report in YYYY-MM-DD format.")


@tool(args_schema=TrafficInput)
async def get_overall_traffic(
    start_date: date, end_date: date, organic_only: bool = False, config: RunnableConfig = {}
) -> str:
    """Fetches the total, aggregated Google Analytics data (sessions, users, etc.) for a given date range. Use for high-level summaries."""
    try:
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
async def get_daily_traffic(
    start_date: date, end_date: date, organic_only: bool = False, config: RunnableConfig = {}
) -> str:
    """Fetches a day-by-day breakdown of Google Analytics data for a given date range. Use for trends and daily performance."""
    try:
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
async def get_traffic_by_countries(
    start_date: date,
    end_date: date,
    limit: int = 10,
    search: Optional[str] = None,
    config: RunnableConfig = {},
) -> str:
    """Fetches a list of countries ranked by traffic metrics for a given date range."""
    try:
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
async def get_daily_traffic_for_country(
    country: str, start_date: date, end_date: date, config: RunnableConfig = {}
) -> str:
    """Fetches a day-by-day traffic breakdown for a single, specific country."""
    try:
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
async def get_traffic_by_pages(
    start_date: date,
    end_date: date,
    limit: int = 10,
    search: Optional[str] = None,
    config: RunnableConfig = {},
) -> str:
    """Fetches a list of website pages ranked by traffic metrics for a given date range."""
    try:
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
async def get_daily_traffic_for_page(
    page_path: str, start_date: date, end_date: date, config: RunnableConfig = {}
) -> str:
    """Fetches a day-by-day traffic breakdown for a single, specific page path."""
    try:
        settings = get_settings()
        token = config.get("configurable", {}).get("auth_token")
        if not token:
            return "Error: Authentication token was not provided to the tool."
        client = GoogleAnalyticsClient(base_url=str(settings.data_service_base_url), token=token)

        data = await client.fetch_page_detail_data(page_path, start_date, end_date)
        return format_response(data)
    except APIError as e:
        return f"Error fetching traffic for page {page_path}: {e.message}"
