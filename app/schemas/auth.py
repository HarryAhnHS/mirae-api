from pydantic import BaseModel
from typing import Optional
from datetime import datetime

# --- Profiles (auth.users.id -> profiles.id) ---
class UserProfile(BaseModel):
    id: str  # auth.users.id
    display_name: Optional[str]
    avatar_url: Optional[str]
    school: Optional[str]
    role: Optional[str]
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None