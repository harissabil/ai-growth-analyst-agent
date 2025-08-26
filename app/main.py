from fastapi import FastAPI

from app.routers.chat import router

app = FastAPI()

app.include_router(router, prefix="/chat", tags=["Chat"])


@app.get("/")
async def root():
    return {"message": "AI Growth Analyst Agent is running"}
