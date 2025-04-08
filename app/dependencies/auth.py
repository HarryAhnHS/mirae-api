from fastapi import Depends, Header, HTTPException
from supabase import create_client
import os

async def user_supabase_client(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid token format")

    token = authorization.split(" ")[1]

    supabase = create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_KEY")
    )

    try:
        user_res = supabase.auth.get_user(token)
    except Exception as e:
        print("Supabase token validation error:", e)
        raise HTTPException(status_code=401, detail="Invalid Supabase token")

    if not user_res.user:
        raise HTTPException(status_code=401, detail="User not found")

    return {
        "supabase": supabase,
        "user_id": user_res.user.id,
        "user": user_res.user,
    }
