from fastapi import APIRouter
from app.services.supabase import supabase
from app.schemas.objective import Objective, Goal, SubjectArea

router = APIRouter()

# Subject Areas
@router.post("/subject-area")
def create_subject_area(subject: SubjectArea):
    return supabase.table("subject_areas").insert(subject.dict()).execute().data

@router.put("/subject-area/{id}")
def update_subject_area(id: str, subject: SubjectArea):
    return supabase.table("subject_areas").update(subject.dict()).eq("id", id).execute().data

@router.delete("/subject-area/{id}")
def delete_subject_area(id: str):
    supabase.table("subject_areas").delete().eq("id", id).execute()
    return {"message": "Deleted"}

# Goals
@router.post("/goal")
def create_goal(goal: Goal):
    return supabase.table("goals").insert(goal.dict()).execute().data

@router.put("/goal/{id}")
def update_goal(id: str, goal: Goal):
    return supabase.table("goals").update(goal.dict()).eq("id", id).execute().data

@router.delete("/goal/{id}")
def delete_goal(id: str):
    supabase.table("goals").delete().eq("id", id).execute()
    return {"message": "Deleted"}

# Objectives
@router.post("/")
def create_objective(obj: Objective):
    return supabase.table("objectives").insert(obj.dict()).execute().data

@router.put("/{id}")
def update_objective(id: str, obj: Objective):
    return supabase.table("objectives").update(obj.dict()).eq("id", id).execute().data

@router.delete("/{id}")
def delete_objective(id: str):
    supabase.table("objectives").delete().eq("id", id).execute()
    return {"message": "Deleted"}
