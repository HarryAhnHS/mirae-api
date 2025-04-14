from pydantic import BaseModel, RootModel
from typing import Optional, List
from datetime import datetime

# --- Sessions ---

class SessionCreate(BaseModel):
    student_id: str
    objective_id: str
    objective_progress_id: str
    memo: Optional[str] = None

# --- Sessions with Progress ---
class ObjectiveProgressCreate(BaseModel):
    trials_completed: int
    trials_total: int

class SessionWithProgressCreate(BaseModel):
    student_id: str
    objective_id: str
    memo: Optional[str] = None
    created_at: Optional[str] = None
    objective_progress: ObjectiveProgressCreate

class SessionsWithProgressCreate(RootModel):
    root: List[SessionWithProgressCreate]