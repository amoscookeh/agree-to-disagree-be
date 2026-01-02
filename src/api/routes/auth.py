from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from jose import jwt
from passlib.context import CryptContext

from src.api.deps import require_auth
from src.config import settings
from src.db.client import get_supabase
from src.db.models import TokenResponse, UserCreate, UserLogin, UserResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_token(user_id: str) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=settings.jwt_expire_minutes)
    return jwt.encode(
        {"sub": user_id, "exp": expire},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


@router.post("/register", response_model=TokenResponse)
async def register(data: UserCreate):
    supabase = get_supabase()
    existing = (
        supabase.table("users").select("id").eq("username", data.username).execute()
    )

    if existing.data:
        raise HTTPException(status_code=400, detail="Username already exists")

    hashed = pwd_context.hash(data.password)
    result = (
        supabase.table("users")
        .insert(
            {
                "username": data.username,
                "password_hash": hashed,
            }
        )
        .execute()
    )

    user = result.data[0]
    token = create_token(user["id"])

    return TokenResponse(access_token=token, user=UserResponse(**user))


@router.post("/login", response_model=TokenResponse)
async def login(data: UserLogin):
    supabase = get_supabase()
    result = (
        supabase.table("users")
        .select("*")
        .eq("username", data.username)
        .single()
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user = result.data
    if not pwd_context.verify(data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_token(user["id"])
    return TokenResponse(access_token=token, user=UserResponse(**user))


@router.get("/me", response_model=UserResponse)
async def me(user: dict = Depends(require_auth)):
    return UserResponse(**user)


@router.get("/check-username")
async def check_username(username: str):
    supabase = get_supabase()
    result = supabase.table("users").select("id").eq("username", username).execute()
    return {"exists": len(result.data) > 0}
