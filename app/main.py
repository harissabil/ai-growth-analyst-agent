from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv(), override=False)

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.errors.error import APIError
from app.errors.handlers import (
    api_error_handler,
    http_exception_handler,
    validation_exception_handler,
)
from app.routers.chat import router
from app.storage.db import engine
from app.storage.models import Base

app = FastAPI()


@app.on_event("startup")
def _init_db():
    Base.metadata.create_all(bind=engine)


app.add_exception_handler(APIError, api_error_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)

app.include_router(router, prefix="/chat", tags=["Chat"])


@app.get("/")
async def root():
    return {"message": "AI Growth Analyst Agent is running"}
