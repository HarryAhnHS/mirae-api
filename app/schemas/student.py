from pydantic import BaseModel
from typing import Optional

class Student(BaseModel):
    id: Optional[str] = None
    teacher_id: str
    name: str
    grade_level: Optional[str] = None
    disability_type: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None