from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from src.config import settings
from src.db.client import get_supabase

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict | None:
    """returns user dict if authenticated, None if not"""
    if not credentials:
        return None

    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        user_id = payload.get("sub")
        if not user_id:
            return None

        supabase = get_supabase()
        result = (
            supabase.table("users").select("*").eq("id", user_id).single().execute()
        )
        return result.data
    except JWTError:
        return None


async def require_auth(user: dict | None = Depends(get_current_user)) -> dict:
    """raises 401 if not authenticated"""
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


async def check_quota(user: dict = Depends(require_auth)) -> dict:
    """raises 403 if quota exhausted"""
    if user["researches_used"] >= user["max_researches"]:
        raise HTTPException(status_code=403, detail="Research quota exhausted")
    return user
