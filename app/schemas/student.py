from pydantic import BaseModel
from typing import Optional 
from datetime import datetime
# --- Students ---
class Student(BaseModel):
    id: Optional[str] = None
    teacher_id: str
    name: str
    grade_level: Optional[str] = None
    disability_type: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class StudentCreate(BaseModel):
    name: str
    grade_level: Optional[str] = None
    disability_type: Optional[str] = None

class StudentCreateFromPDF(BaseModel):
    pdf_file: bytes
    filename: str