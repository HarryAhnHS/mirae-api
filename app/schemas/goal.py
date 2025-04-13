from pydantic import BaseModel
from typing import Optional
from datetime import datetime

# --- Profiles (auth.users.id -> profiles.id) ---
class CreateGoal(BaseModel):
    subject_area_id: str
    title: str
    student_id: str