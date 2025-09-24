from fastapi import HTTPException, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from typing import Tuple

from app.clients.auth_client import auth_client

bearer_scheme = HTTPBearer(scheme_name="Bearer", description="Enter your Bearer token", bearerFormat="JWT")


async def verify_token_and_get_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> Tuple[str, str]:
    """
    Verify the bearer token and return both the token and user_id.

    Args:
        credentials: HTTPAuthorizationCredentials from FastAPI Security

    Returns:
        Tuple of (token, user_id)

    Raises:
        HTTPException: If token is invalid or user verification fails
    """
    token = credentials.credentials

    user_id = await auth_client.verify_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return token, user_id
