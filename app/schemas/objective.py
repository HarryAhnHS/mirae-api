from pydantic import BaseModel, Field
from uuid import UUID
from typing import Optional
from datetime import datetime

# --- Subject Areas ---
class SubjectArea(BaseModel):
    id: Optional[str] = None
    name: str
    teacher_id: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class CreateSubjectArea(BaseModel):
    name: str


# --- Objectives ---
class Objective(BaseModel):
    id: Optional[str] = None
    student_id: str
    teacher_id: str
    subject_area_id: str
    description: str
    progress_type: Optional[str] = "general"
    current_progress: Optional[int] = 0
    weekly_frequency: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class CreateObjective(BaseModel):
    student_id: str
    goal_id: UUID
    subject_area_id: UUID
    description: str = Field(..., description="Full IEP-style description")
    objective_type: str = Field(..., description="Either 'binary' or 'trial'")
    target_accuracy: float = Field(..., ge=0.0, le=1.0, description="Required accuracy threshold (0.0 - 1.0)")
    target_consistency_trials: int = Field(..., gt=0, description="Minimum number of successful trials")
    target_consistency_successes: int = Field(..., gt=0, description="Successes required for consistency")


