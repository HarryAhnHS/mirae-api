from pydantic import BaseModel
from typing import Optional
from datetime import datetime

# --- Sessions ---
class Session(BaseModel):
    id: Optional[str] = None
    teacher_id: str
    student_id: str
    objective_id: str
    raw_input: str
    llm_summary: Optional[str] = None
    progress_delta: int
    notes: Optional[str] = None
    date: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class SessionCreate(BaseModel):
    student_id: str
    objective_id: str
    raw_input: str
    llm_summary: Optional[str] = None
    progress_delta: int
