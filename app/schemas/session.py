from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class Session(BaseModel):
    id: Optional[str] = None
    objective_id: str
    raw_input: str
    llm_summary: Optional[str] = None
    progress_delta: int
    notes: Optional[str] = None
    date: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None