from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .error import APIError


async def api_error_handler(request: Request, exc: APIError):
    """
    Handler for the custom APIError.
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.message, "statusCode": exc.status_code},
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """
    Handler for FastAPI's built-in HTTPException (and Starlette's).
    This will catch errors from security dependencies and other built-in features.
    """
    # For the 401/403 from the security scheme, the detail is the message.
    message = exc.detail if exc.detail else "An HTTP error occurred."

    # Standardize the message for the authentication error
    if exc.status_code == 401 and exc.detail == "Not authenticated":
        message = "Unauthorized: Missing or invalid authentication token."

    return JSONResponse(
        status_code=exc.status_code,
        content={"message": message, "statusCode": exc.status_code},
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handler for Pydantic's RequestValidationError.
    This catches errors when the request body is invalid.
    """
    return JSONResponse(
        status_code=422,  # Unprocessable Entity
        content={
            "message": "Validation Error: The request data is invalid.",
            "statusCode": 422,
        },
    )
