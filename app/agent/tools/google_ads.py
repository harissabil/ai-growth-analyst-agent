import json
from datetime import date

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from app.clients.google_ads_client import GoogleAdsClient
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
class AdsTrafficInput(BaseModel):
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


class AdsCampaignDetailInput(BaseModel):
    campaign_id: str = Field(
        ...,
        description="Exact Google Ads campaign id (path param).",
    )
    start_date: date = Field(..., description="Start date in YYYY-MM-DD (resolve relative dates first).")
    end_date: date = Field(..., description="End date in YYYY-MM-DD (resolve relative dates first).")


# Tools
@tool(args_schema=AdsTrafficInput)
async def get_google_ads_overall(start_date: date, end_date: date, config: RunnableConfig = {}) -> str:
    """
    Source: Google Ads
    Purpose: High-level totals for a date range (impressions, currency, spend, conversion_rate_percent, ctr_percent, roi_percent).
    Required: start_date, end_date (absolute dates).
    """
    try:
        settings = get_settings()
        token = config.get("configurable", {}).get("auth_token")
        if not token:
            return "Error: Authentication token was not provided to the tool."

        client = GoogleAdsClient(base_url=str(settings.data_service_base_url), token=token)
        data = await client.fetch_overall_data(start_date, end_date)
        return format_response(data)
    except APIError as e:
        return f"Error fetching Google Ads overall: {e.errors}"


@tool(args_schema=AdsTrafficInput)
async def get_google_ads_daily(start_date: date, end_date: date, config: RunnableConfig = {}) -> str:
    """
    Source: Google Ads
    Purpose: Daily time series for a date range (impressions, currency, spend, conversion_rate_percent, ctr_percent, roi_percent).
    Required: start_date, end_date (absolute dates).
    """
    try:
        settings = get_settings()
        token = config.get("configurable", {}).get("auth_token")
        if not token:
            return "Error: Authentication token was not provided to the tool."

        client = GoogleAdsClient(base_url=str(settings.data_service_base_url), token=token)
        data = await client.fetch_daily_data(start_date, end_date)
        return format_response(data)
    except APIError as e:
        return f"Error fetching Google Ads daily: {e.errors}"


@tool(args_schema=AdsTrafficInput)
async def get_google_ads_campaigns(start_date: date, end_date: date, config: RunnableConfig = {}) -> str:
    """
    Source: Google Ads
    Purpose: List campaigns (id, name, status) with metrics (impressions, currency, spend, conversion_rate_percent, ctr_percent, roi_percent).
    Required: start_date, end_date (absolute dates).
    """
    try:
        settings = get_settings()
        token = config.get("configurable", {}).get("auth_token")
        if not token:
            return "Error: Authentication token was not provided to the tool."

        client = GoogleAdsClient(base_url=str(settings.data_service_base_url), token=token)
        data = await client.fetch_campaigns_data(start_date, end_date)
        return format_response(data)
    except APIError as e:
        return f"Error fetching Google Ads campaigns: {e.errors}"


@tool(args_schema=AdsCampaignDetailInput)
async def get_google_ads_daily_for_campaign(
    campaign_id: str, start_date: date, end_date: date, config: RunnableConfig = {}
) -> str:
    """
    Source: Google Ads
    Purpose: Daily breakdown for a single campaign over a date range.
    Required: campaign_id (exact), start_date, end_date (absolute).
    """
    try:
        settings = get_settings()
        token = config.get("configurable", {}).get("auth_token")
        if not token:
            return "Error: Authentication token was not provided to the tool."

        client = GoogleAdsClient(base_url=str(settings.data_service_base_url), token=token)
        data = await client.fetch_campaign_detail_data(campaign_id, start_date, end_date)
        return format_response(data)
    except APIError as e:
        return f"Error fetching Google Ads for campaign '{campaign_id}': {e.errors}"
