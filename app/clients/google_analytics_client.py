import logging
from datetime import date
from typing import Any, List, Literal, Optional

import httpx
from pydantic import BaseModel, Field

from app.errors.error import APIError

logger = logging.getLogger(__name__)


def _extract_errors(payload: Any) -> List[str]:
    """
    Accepts:
      {"errors": "google oauth required"}
      {"errors": ["a", "b"]}
      {"message": "Something"}                # your old shape
      other
    Returns a list[str]
    """
    try:
        if isinstance(payload, dict):
            if "errors" in payload:
                val = payload["errors"]
                if isinstance(val, list):
                    return [str(x) for x in val if str(x).strip()]
                if isinstance(val, str):
                    return [val]
            if "message" in payload and payload["message"]:
                return [str(payload["message"])]
    except Exception:
        pass
    return ["An unknown API error occurred."]


class BaseAnalyticsData(BaseModel):
    sessions: int
    screen_page_views: int = Field(..., alias="screenPageViews")  # Handle potential camelCase from API
    bounce_rate_percent: float = Field(..., alias="bounceRatePercent")
    average_session_duration_seconds: float = Field(..., alias="averageSessionDurationSeconds")
    active_users: int = Field(..., alias="activeUsers")

    class Config:
        populate_by_name = True  # Allows using both snake_case and alias


class DailyAnalyticsData(BaseAnalyticsData):
    date: date


class CountryAnalyticsData(BaseAnalyticsData):
    country: str


class PageAnalyticsData(BaseAnalyticsData):
    page: str
    title: str


class GoogleAnalyticsClient:
    """
    An asynchronous client to interact with the Google Analytics microservice.
    """

    def __init__(self, base_url: str, token: str):
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {token}"}
        self.client = httpx.AsyncClient(base_url=self.base_url, headers=self.headers, timeout=20.0)

    async def _make_request(self, method: str, endpoint: str, params: Optional[dict] = None) -> Any:
        """Helper method to make and handle HTTP requests."""
        try:
            logger.info(f"Making request to {endpoint} with params: {params}")
            response = await self.client.request(method, endpoint, params=params)
            response.raise_for_status()  # Raises HTTPStatusError for 4xx/5xx responses
            return response.json()
        except httpx.HTTPStatusError as e:
            # Try to parse error response
            try:
                error_data = e.response.json()
            except Exception:
                error_data = {"message": e.response.text}
            errors = _extract_errors(error_data)
            logger.error(f"[GA] HTTP error: {e.response.status_code} - {errors}")
            raise APIError(status_code=e.response.status_code, errors=errors)
        except httpx.RequestError as e:
            logger.error(f"[GA] Request error: {e}")
            # 503 is a better fit for connectivity issues
            raise APIError(status_code=503, errors=[f"Failed to connect to the service: {e}"])

    async def fetch_overall_data(
        self, start_date: date, end_date: date, organic_only: bool = False
    ) -> BaseAnalyticsData:
        """Fetches overall analytics data."""
        endpoint = "/google-analytics/overall-organic-traffic" if organic_only else "/google-analytics/overall"
        params = {"start_date": start_date.isoformat(), "end_date": end_date.isoformat()}
        response_data = await self._make_request("GET", endpoint, params=params)
        return BaseAnalyticsData.model_validate(response_data["data"])

    async def fetch_daily_data(
        self, start_date: date, end_date: date, organic_only: bool = False
    ) -> List[DailyAnalyticsData]:
        """Fetches daily analytics data."""
        endpoint = "/google-analytics/daily-organic-traffic" if organic_only else "/google-analytics/daily"
        params = {"start_date": start_date.isoformat(), "end_date": end_date.isoformat()}
        response_data = await self._make_request("GET", endpoint, params=params)
        return [DailyAnalyticsData.model_validate(item) for item in response_data["data"]]

    async def fetch_countries_data(
        self,
        start_date: date,
        end_date: date,
        order_by: Literal["asc", "desc"] = "desc",
        limit: int = 10,
        search: Optional[str] = None,
    ) -> List[CountryAnalyticsData]:
        """Fetches analytics data grouped by country."""
        endpoint = "/google-analytics/countries"
        params = {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "order_by": order_by,
            "limit": limit,
        }
        if search:
            params["search"] = search
        response_data = await self._make_request("GET", endpoint, params=params)
        return [CountryAnalyticsData.model_validate(item) for item in response_data["data"]]

    async def fetch_country_detail_data(
        self, country: str, start_date: date, end_date: date
    ) -> List[DailyAnalyticsData]:
        """Fetches daily analytics for a specific country."""
        endpoint = f"/google-analytics/countries/{country.lower()}"
        params = {"start_date": start_date.isoformat(), "end_date": end_date.isoformat()}
        response_data = await self._make_request("GET", endpoint, params=params)
        return [DailyAnalyticsData.model_validate(item) for item in response_data["data"]]

    async def fetch_pages_data(
        self,
        start_date: date,
        end_date: date,
        order_by: Literal["asc", "desc"] = "desc",
        limit: int = 10,
        search: Optional[str] = None,
    ) -> List[PageAnalyticsData]:
        """Fetches analytics data grouped by page."""
        endpoint = "/google-analytics/pages"
        params = {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "order_by": order_by,
            "limit": limit,
        }
        if search:
            params["search"] = search
        response_data = await self._make_request("GET", endpoint, params=params)
        return [PageAnalyticsData.model_validate(item) for item in response_data["data"]]

    async def fetch_page_detail_data(
        self, page_path: str, start_date: date, end_date: date
    ) -> List[DailyAnalyticsData]:
        """Fetches daily analytics for a specific page."""
        # The page path needs to be URL encoded if it contains special characters,
        # but httpx handles this automatically for path parameters.
        endpoint = f"/google-analytics/pages/{page_path}"
        params = {"start_date": start_date.isoformat(), "end_date": end_date.isoformat()}
        response_data = await self._make_request("GET", endpoint, params=params)
        return [DailyAnalyticsData.model_validate(item) for item in response_data["data"]]
