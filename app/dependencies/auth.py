# app/dependencies/auth.py
# decode the JWT token and return the logged user's supabase client

from fastapi import HTTPException, Request
import jwt
from supabase import create_client
import os

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")

async def user_supabase_client(request: Request):
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not token:
        raise HTTPException(status_code=401, detail="Missing token")

    try:
        payload = jwt.decode(token, SUPABASE_JWT_SECRET, algorithms=["HS256"])
        user_id = payload["sub"]
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid Supabase token")

    # Create a user-scoped Supabase client
    supabase = create_client(SUPABASE_URL, token)
    return {"supabase": supabase, "user_id": user_id}
