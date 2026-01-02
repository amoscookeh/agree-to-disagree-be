from fastapi import APIRouter, Depends, HTTPException

from src.api.deps import require_auth
from src.db.client import get_supabase
from src.db.models import WaitlistJoin

router = APIRouter(prefix="/api", tags=["waitlist"])


@router.post("/waitlist")
async def join_waitlist(data: WaitlistJoin, user: dict = Depends(require_auth)):
    supabase = get_supabase()

    existing_email = (
        supabase.table("users")
        .select("id")
        .eq("email", data.email)
        .neq("id", user["id"])
        .execute()
    )

    if existing_email.data:
        raise HTTPException(status_code=400, detail="Email already in use")

    supabase.table("users").update({"email": data.email}).eq("id", user["id"]).execute()

    return {"message": "Email added successfully", "email": data.email}
