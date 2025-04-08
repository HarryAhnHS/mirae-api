from pydantic import BaseModel
from typing import Optional

class SubjectArea(BaseModel):
    id: Optional[str] = None
    name: str
    created_at: Optional[str] = None

class Goal(BaseModel):
    id: Optional[str] = None
    subject_area_id: str
    title: str
    created_at: Optional[str] = None

class Objective(BaseModel):
    id: Optional[str] = None
    goal_id: str
    description: str
    progress_type: Optional[str] = "general"
    current_progress: Optional[int] = 0
    weekly_frequency: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None