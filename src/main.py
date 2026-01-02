from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import health_router, research_router
from src.config import settings
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

app = FastAPI(
    title="Agree to Disagree API",
    description="Backend API for balanced political research",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", settings.openrouter_site_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(research_router)


@app.get("/")
async def root():
    return {"message": "Agree to Disagree API", "status": "running"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
