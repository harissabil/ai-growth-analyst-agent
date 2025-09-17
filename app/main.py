import logging
from contextlib import asynccontextmanager

from dotenv import find_dotenv, load_dotenv
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.errors.error import APIError
from app.errors.handlers import (
    api_error_handler,
    http_exception_handler,
    validation_exception_handler,
)
from app.routers.chat import router as chat_router
from app.storage.cosmos_db import cosmos_client

# Load environment variables
load_dotenv(find_dotenv(), override=False)

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    # Startup
    logger.info("Initializing Cosmos DB containers...")
    try:
        cosmos_client.initialize_containers()
        logger.info("Cosmos DB initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Cosmos DB: {e}")
        raise

    yield

    # Shutdown
    logger.info("Application shutting down...")


# Create FastAPI app
app = FastAPI(
    title="AI Growth Analyst Agent API",
    description="REST API for AI-Powered Growth Analyst",
    version="0.0.1",
    lifespan=lifespan,
)

# Configure CORS (adjust origins based on your requirements)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add exception handlers
app.add_exception_handler(APIError, api_error_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)

# Include routers
app.include_router(chat_router, prefix="/chat", tags=["Chat"])


@app.get("/")
async def root():
    """Root endpoint for health check."""
    return {"message": "AI Growth Analyst Agent is running", "storage": "Azure Cosmos DB", "version": "2.0.0"}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Verify Cosmos DB connection
        history_container = cosmos_client.get_history_container()
        # Simple read to verify connection
        _ = history_container.read()

        return {"status": "healthy", "database": "connected", "service": "AI Growth Analyst Agent"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}
