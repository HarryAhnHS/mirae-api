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