import logging
from datetime import date
from typing import Any, List, Optional

import httpx
from pydantic import BaseModel

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
class BaseAdsData(BaseModel):
    impressions: int
    currency: str
    spend: float
    conversion_rate_percent: float
    ctr_percent: float
    roi_percent: float

    class Config:
        populate_by_name = True


class DailyAdsData(BaseAdsData):
    date: date


class CampaignSummaryData(BaseAdsData):
    id: str
    name: str
    status: str


# Client
class GoogleAdsClient:
    """
    Async client for the Google Ads microservice.
    Mirrors GA/GSC clients' ergonomics and error handling.
    """

    def __init__(self, base_url: str, token: str, timeout: float = 20.0):
        self.base_url = base_url.rstrip("/")
        self.headers = {"Authorization": f"Bearer {token}"}
        self.client = httpx.AsyncClient(base_url=self.base_url, headers=self.headers, timeout=timeout)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.aclose()

    async def aclose(self):
        await self.client.aclose()

    async def _make_request(self, method: str, endpoint: str, params: Optional[dict] = None) -> Any:
        try:
            logger.info(f"[ADS] {method} {endpoint} params={params}")
            resp = await self.client.request(method, endpoint, params=params)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            try:
                error_data = e.response.json()
            except Exception:
                error_data = {"message": e.response.text}
            errors = _extract_errors(error_data)
            logger.error(f"[ADS] HTTP {e.response.status_code}: {errors}")
            raise APIError(status_code=e.response.status_code, errors=errors)
        except httpx.RequestError as e:
            logger.error(f"[ADS] Request error: {e}")
            raise APIError(status_code=503, errors=[f"Failed to connect to the service: {e}"])

    # Endpoints
    async def fetch_overall_data(self, start_date: date, end_date: date) -> BaseAdsData:
        """
        GET /google-ads/overall
        """
        params = {"start_date": start_date.isoformat(), "end_date": end_date.isoformat()}
        data = await self._make_request("GET", "/google-ads/overall", params=params)
        return BaseAdsData.model_validate(data["data"])

    async def fetch_daily_data(self, start_date: date, end_date: date) -> List[DailyAdsData]:
        """
        GET /google-ads/daily
        """
        params = {"start_date": start_date.isoformat(), "end_date": end_date.isoformat()}
        data = await self._make_request("GET", "/google-ads/daily", params=params)
        return [DailyAdsData.model_validate(item) for item in data["data"]]

    async def fetch_campaigns_data(self, start_date: date, end_date: date) -> List[CampaignSummaryData]:
        """
        GET /google-ads/campaigns
        """
        params = {"start_date": start_date.isoformat(), "end_date": end_date.isoformat()}
        data = await self._make_request("GET", "/google-ads/campaigns", params=params)
        return [CampaignSummaryData.model_validate(item) for item in data["data"]]

    async def fetch_campaign_detail_data(
        self, campaign_id: str, start_date: date, end_date: date
    ) -> List[DailyAdsData]:
        """
        GET /google-ads/campaigns/{id}
        Path requires an exact campaign id.
        """
        endpoint = f"/google-ads/campaigns/{campaign_id}"
        params = {"start_date": start_date.isoformat(), "end_date": end_date.isoformat()}
        data = await self._make_request("GET", endpoint, params=params)
        return [DailyAdsData.model_validate(item) for item in data["data"]]
