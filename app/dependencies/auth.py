from fastapi import Depends, Header, HTTPException
from supabase import create_client
import os
import time
import logging

logger = logging.getLogger(__name__)

async def user_supabase_client(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid token format")

    token = authorization.split(" ")[1]

    # Create Supabase client with timeout settings
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    
    if not supabase_url or not supabase_key:
        logger.error("Supabase URL or Key not found in environment variables")
        raise HTTPException(status_code=500, detail="Server configuration error")
    
    try:
        start_time = time.time()
        logger.info("Creating Supabase client")
        supabase = create_client(supabase_url, supabase_key)
        
        # Set a longer timeout for this specific request
        logger.info("Validating token with Supabase")
        user_res = supabase.auth.get_user(token)
        end_time = time.time()
        logger.info(f"Token validation completed in {end_time - start_time:.2f} seconds")
    except Exception as e:
        logger.error(f"Supabase token validation error: {str(e)}")
        if "timed out" in str(e).lower():
            raise HTTPException(
                status_code=504, 
                detail="Connection to authentication service timed out. Please try again later."
            )
        raise HTTPException(status_code=401, detail=f"Authentication error: {str(e)}")

    if not user_res.user:
        logger.warning("User not found after successful token validation")
        raise HTTPException(status_code=401, detail="User not found")

    logger.info(f"Successfully authenticated user: {user_res.user.id}")
    return {
        "supabase": supabase,
        "user_id": user_res.user.id,
        "user": user_res.user,
    }
