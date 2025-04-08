from fastapi import APIRouter, Request, HTTPException
from app.schemas.auth import UserProfile
from app.services.supabase import supabase
from datetime import datetime, timedelta
import jwt
import os

router = APIRouter()

JWT_SECRET = os.getenv("JWT_SECRET", "devsecret")
JWT_ALGORITHM = "HS256"

@router.post("/login")
def login(profile: UserProfile):
    # Create or update educator in Supabase
    user_id = profile.id
    existing = supabase.table("educators").select("*").eq("id", user_id).execute()
    if not existing.data:
        supabase.table("educators").insert(profile.dict()).execute()
    
    # Return a JWT token (valid for 1 hour)
    token = jwt.encode(
        {"sub": user_id, "exp": datetime.utcnow() + timedelta(hours=1)},
        JWT_SECRET,
        algorithm=JWT_ALGORITHM
    )
    return {"token": token}

@router.get("/me")
def get_me(request: Request):
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload["sub"]
        result = supabase.table("educators").select("*").eq("id", user_id).single().execute()
        return {"user": result.data}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Session expired")
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid token")
