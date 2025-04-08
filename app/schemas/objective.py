from pydantic import BaseModel
from typing import Optional
from datetime import datetime

# --- Subject Areas ---
class SubjectArea(BaseModel):
    id: Optional[str] = None
    name: str
    teacher_id: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

# --- Objectives ---
class Objective(BaseModel):
    id: Optional[str] = None
    student_id: str
    teacher_id: str
    description: str
    progress_type: Optional[str] = "general"
    current_progress: Optional[int] = 0
    weekly_frequency: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
