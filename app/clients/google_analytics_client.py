import logging
from datetime import date
from typing import Any, List, Literal, Optional

import httpx
from pydantic import BaseModel, Field

from app.clients.errors.errors import APIError

logger = logging.getLogger(__name__)


class BaseAnalyticsData(BaseModel):
    sessions: int
    screen_page_views: int = Field(
        ..., alias="screenPageViews"
    )  # Handle potential camelCase from API
    bounce_rate: float = Field(..., alias="bounceRate")
    average_session_duration: float = Field(..., alias="averageSessionDuration")
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
            error_data = e.response.json()
            error_message = error_data.get("message", "An unknown API error occurred.")
            logger.error(f"HTTP error occurred: {e.response.status_code} - {error_message}")
            raise APIError(status_code=e.response.status_code, message=error_message)
        except httpx.RequestError as e:
            logger.error(f"Request error occurred: {e}")
            raise APIError(status_code=500, message=f"Failed to connect to the service: {e}")

    async def fetch_overall_data(
        self, start_date: date, end_date: date, organic_only: bool = False
    ) -> BaseAnalyticsData:
        """Fetches overall analytics data."""
        endpoint = (
            "/google/analytics/overall-organic-traffic"
            if organic_only
            else "/google/analytics/overall"
        )
        params = {"start_date": start_date.isoformat(), "end_date": end_date.isoformat()}
        response_data = await self._make_request("GET", endpoint, params=params)
        return BaseAnalyticsData.model_validate(response_data["data"])

    async def fetch_daily_data(
        self, start_date: date, end_date: date, organic_only: bool = False
    ) -> List[DailyAnalyticsData]:
        """Fetches daily analytics data."""
        endpoint = (
            "/google/analytics/daily-organic-traffic" if organic_only else "/google/analytics/daily"
        )
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
        endpoint = "/google/analytics/countries"
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
        endpoint = f"/google/analytics/countries/{country.lower()}"
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
        endpoint = "/google/analytics/pages"
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
        endpoint = f"/google/analytics/pages/{page_path}"
        params = {"start_date": start_date.isoformat(), "end_date": end_date.isoformat()}
        response_data = await self._make_request("GET", endpoint, params=params)
        return [DailyAnalyticsData.model_validate(item) for item in response_data["data"]]
