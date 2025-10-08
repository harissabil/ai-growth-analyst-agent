from typing import Optional

import httpx

from app.config import get_settings


class AuthClient:
    """Client for interacting with the authentication service."""

    def __init__(self):
        settings = get_settings()
        self.base_url = str(settings.data_service_base_url).rstrip("/")
        self.timeout = 30.0

    async def verify_token(self, token: str) -> Optional[str]:
        """
        Verify a bearer token and return the user ID if valid.

        Args:
            token: The bearer token to verify

        Returns:
            User ID if token is valid, None otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/auth/profile", headers={"Authorization": f"Bearer {token}", "accept": "*/*"}
                )

                if response.status_code == 200:
                    data = response.json()
                    return data.get("id")
                else:
                    return None

        except Exception:
            # Log the error if needed, but don't expose it
            return None


# Global instance
auth_client = AuthClient()
