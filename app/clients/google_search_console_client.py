import logging
from datetime import date
from typing import Any, List, Optional

import httpx
from pydantic import BaseModel, Field

from app.errors.error import APIError

logger = logging.getLogger(__name__)


def _extract_errors(payload: Any) -> List[str]:
    """
    Accepts:
      {"errors": "google oauth required"}
      {"errors": ["a", "b"]}
      {"message": "Something"}                # legacy shape
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


# Pydantic response models
class BaseSearchConsoleData(BaseModel):
    clicks: int
    impressions: int
    ctr_percent: float = Field(..., alias="ctr_percent")
    average_position: float = Field(..., alias="average_position")

    class Config:
        populate_by_name = True


class DailySearchConsoleData(BaseSearchConsoleData):
    date: date


class KeywordSearchConsoleData(BaseSearchConsoleData):
    keyword: str


class CountrySearchConsoleData(BaseSearchConsoleData):
    country: str


# Client
class GoogleSearchConsoleClient:
    """
    Async client for your Google Search Console microservice.
    Matches GA client's shape and error handling.
    """
    def __init__(self, base_url: str, token: str, timeout: float = 20.0):
        self.base_url = base_url.rstrip("/")
        self.headers = {"Authorization": f"Bearer {token}"}
        self.client = httpx.AsyncClient(base_url=self.base_url, headers=self.headers, timeout=timeout)

    # Allow usage as async context manager
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.aclose()

    async def aclose(self):
        await self.client.aclose()

    async def _make_request(self, method: str, endpoint: str, params: Optional[dict] = None) -> Any:
        try:
            logger.info(f"[GSC] {method} {endpoint} params={params}")
            resp = await self.client.request(method, endpoint, params=params)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            try:
                error_data = e.response.json()
            except Exception:
                error_data = {"message": e.response.text}
            errors = _extract_errors(error_data)
            logger.error(f"[GSC] HTTP {e.response.status_code}: {errors}")
            raise APIError(status_code=e.response.status_code, errors=errors)
        except httpx.RequestError as e:
            logger.error(f"[GSC] Request error: {e}")
            raise APIError(status_code=503, errors=[f"Failed to connect to the service: {e}"])

    # -------- Endpoints --------

    async def fetch_overall_data(self, start_date: date, end_date: date) -> BaseSearchConsoleData:
        """
        GET /google-search-console/overall
        """
        params = {"start_date": start_date.isoformat(), "end_date": end_date.isoformat()}
        data = await self._make_request("GET", "/google-search-console/overall", params=params)
        return BaseSearchConsoleData.model_validate(data["data"])

    async def fetch_daily_data(self, start_date: date, end_date: date) -> List[DailySearchConsoleData]:
        """
        GET /google-search-console/daily
        """
        params = {"start_date": start_date.isoformat(), "end_date": end_date.isoformat()}
        data = await self._make_request("GET", "/google-search-console/daily", params=params)
        return [DailySearchConsoleData.model_validate(item) for item in data["data"]]

    async def fetch_keywords_data(
            self,
            start_date: date,
            end_date: date,
            limit: int = 10,
            search: Optional[str] = None,
    ) -> List[KeywordSearchConsoleData]:
        """
        GET /google-search-console/keywords
        Optional 'search' filters keywords containing the term (case-insensitive).
        """
        params = {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "limit": int(limit),
        }
        if search:
            params["search"] = search
        data = await self._make_request("GET", "/google-search-console/keywords", params=params)
        return [KeywordSearchConsoleData.model_validate(item) for item in data["data"]]

    async def fetch_keyword_detail_data(
            self,
            keyword: str,
            start_date: date,
            end_date: date,
    ) -> List[DailySearchConsoleData]:
        """
        GET /google-search-console/keywords/{keyword}
        Keyword path must be the exact keyword (URL-encoded automatically by httpx for path segments).
        """
        endpoint = f"/google-search-console/keywords/{keyword}"
        params = {"start_date": start_date.isoformat(), "end_date": end_date.isoformat()}
        data = await self._make_request("GET", endpoint, params=params)
        return [DailySearchConsoleData.model_validate(item) for item in data["data"]]

    async def fetch_countries_data(
            self,
            start_date: date,
            end_date: date,
            limit: int = 10,
            search: Optional[str] = None,
    ) -> List[CountrySearchConsoleData]:
        """
        GET /google-search-console/countries
        Optional 'search' filters countries containing the term (case-insensitive).
        """
        params = {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "limit": int(limit),
        }
        if search:
            params["search"] = search
        data = await self._make_request("GET", "/google-search-console/countries", params=params)
        return [CountrySearchConsoleData.model_validate(item) for item in data["data"]]

    async def fetch_country_detail_data(
            self,
            country: str,  # can be partial but must be unique per service rules
            start_date: date,
            end_date: date,
    ) -> List[DailySearchConsoleData]:
        """
        GET /google-search-console/countries/{country}
        Country path can be a unique partial match per the service behavior.
        """
        endpoint = f"/google-search-console/countries/{country}"
        params = {"start_date": start_date.isoformat(), "end_date": end_date.isoformat()}
        data = await self._make_request("GET", endpoint, params=params)
        return [DailySearchConsoleData.model_validate(item) for item in data["data"]]
