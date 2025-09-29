import logging
from typing import Any, List, Optional

import httpx
from pydantic import BaseModel, ValidationError

from app.config import get_settings
from app.errors.error import APIError

logger = logging.getLogger(__name__)


class GoogleAnalyticsProperty(BaseModel):
    property_id: str
    property_name: str


class GoogleAnalyticsCurrentConfig(BaseModel):
    property_id: str
    property_name: str


class GoogleAnalyticsConfig(BaseModel):
    connected: bool
    current: Optional[GoogleAnalyticsCurrentConfig]
    options: List[GoogleAnalyticsProperty]


class GoogleSearchConsoleProperty(BaseModel):
    property_type: str
    property_name: str


class GoogleSearchConsoleCurrentConfig(BaseModel):
    property_type: str
    property_name: str


class GoogleSearchConsoleConfig(BaseModel):
    connected: bool
    current: Optional[GoogleSearchConsoleCurrentConfig]
    options: List[GoogleSearchConsoleProperty]


class GoogleAdsCurrentConfig(BaseModel):
    manager_account_developer_token: str
    customer_account_id: str


class GoogleAdsConfig(BaseModel):
    connected: bool
    current: Optional[GoogleAdsCurrentConfig]
    options: List[str]


class PlatformData(BaseModel):
    google_analytics: GoogleAnalyticsConfig
    google_search_console: GoogleSearchConsoleConfig
    google_ads: GoogleAdsConfig


class PlatformResponse(BaseModel):
    message: str
    data: PlatformData


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


class PlatformClient:
    """Client for interacting with the platform service."""

    def __init__(self):
        settings = get_settings()
        self.base_url = str(settings.data_service_base_url).rstrip("/")
        self.timeout = 30.0

    async def get_platform(self, token: str) -> PlatformResponse:
        """
        Get platform information for the authenticated user.

        Args:
            token: Bearer token for authentication

        Returns:
            PlatformResponse containing platform data with google_analytics, google_search_console, and google_ads info

        Raises:
            APIError: If the request fails
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/platform", headers={"Authorization": f"Bearer {token}", "accept": "*/*"}
                )

                if response.status_code == 200:
                    try:
                        data = response.json()
                        return PlatformResponse(**data)
                    except ValidationError as e:
                        logger.error(f"Failed to parse platform response: {e}")
                        raise APIError(status_code=500, errors=[f"Invalid response format: {str(e)}"])
                else:
                    try:
                        error_data = response.json()
                        errors = _extract_errors(error_data)
                    except Exception:
                        errors = [f"Platform request failed with status {response.status_code}"]

                    raise APIError(status_code=response.status_code, errors=errors)

        except httpx.RequestError as e:
            logger.error(f"Network error in platform client: {e}")
            raise APIError(status_code=500, errors=[f"Network error: {str(e)}"])
        except APIError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in platform client: {e}")
            raise APIError(status_code=500, errors=[f"Unexpected error: {str(e)}"])


# Global instance
platform_client = PlatformClient()
