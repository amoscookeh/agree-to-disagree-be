from fastapi import APIRouter

from src.config import settings

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
async def health_check():
    return {"status": "healthy", "environment": settings.environment}
