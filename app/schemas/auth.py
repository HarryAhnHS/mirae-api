from pydantic import BaseModel
from typing import Optional

class UserProfile(BaseModel):
    id: str  # Supabase auth.users.id
    display_name: Optional[str]
    avatar_url: Optional[str]
    school: Optional[str]
    role: Optional[str]