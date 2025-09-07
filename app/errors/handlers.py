from typing import List

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .error import APIError


def _as_errors_list(x) -> List[str]:
    # Accept string | list[str] | dict with 'errors' | anything -> list[str]
    if x is None:
        return ["An unknown error occurred."]
    if isinstance(x, list):
        # ensure all stringified
        return [str(i) for i in x if str(i).strip()]
    if isinstance(x, str):
        return [x]
    if isinstance(x, dict) and "errors" in x:
        return _as_errors_list(x["errors"])
    return [str(x)]


def _format_pydantic_errors(exc: RequestValidationError) -> List[str]:
    out = []
    for err in exc.errors():
        loc = ".".join(str(p) for p in err.get("loc", []) if p not in ("body",))
        msg = err.get("msg", "Invalid value")
        out.append(f"{loc or 'request'}: {msg}")
    return out or ["Validation Error: The request data is invalid."]


async def api_error_handler(request: Request, exc: APIError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"errors": _as_errors_list(exc.errors)},
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    # Preserve helpful 401 message
    message = exc.detail if exc.detail else "An HTTP error occurred."
    if exc.status_code == 401 and exc.detail == "Not authenticated":
        message = "Unauthorized: Missing or invalid authentication token."
    return JSONResponse(
        status_code=exc.status_code,
        content={"errors": _as_errors_list(message)},
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"errors": _format_pydantic_errors(exc)},
    )
