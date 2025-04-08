from fastapi import APIRouter, Depends
from app.schemas.objective import Objective, Goal, SubjectArea
from app.dependencies.auth import user_supabase_client

router = APIRouter()

# -------- Subject Areas --------

@router.post("/subject-area")
def create_subject_area(subject: SubjectArea, context=Depends(user_supabase_client)):
    supabase = context["supabase"]
    return supabase.table("subject_areas").insert(subject.model_dump()).execute().data

@router.put("/subject-area/{id}")
def update_subject_area(id: str, subject: SubjectArea, context=Depends(user_supabase_client)):
    supabase = context["supabase"]
    return supabase.table("subject_areas").update(subject.model_dump()).eq("id", id).execute().data

@router.delete("/subject-area/{id}")
def delete_subject_area(id: str, context=Depends(user_supabase_client)):
    supabase = context["supabase"]
    supabase.table("subject_areas").delete().eq("id", id).execute()
    return {"message": "Deleted"}

# -------- Goals --------

@router.post("/goal")
def create_goal(goal: Goal, context=Depends(user_supabase_client)):
    supabase = context["supabase"]
    return supabase.table("goals").insert(goal.model_dump()).execute().data

@router.put("/goal/{id}")
def update_goal(id: str, goal: Goal, context=Depends(user_supabase_client)):
    supabase = context["supabase"]
    return supabase.table("goals").update(goal.model_dump()).eq("id", id).execute().data

@router.delete("/goal/{id}")
def delete_goal(id: str, context=Depends(user_supabase_client)):
    supabase = context["supabase"]
    supabase.table("goals").delete().eq("id", id).execute()
    return {"message": "Deleted"}

# -------- Objectives --------

@router.post("/")
def create_objective(obj: Objective, context=Depends(user_supabase_client)):
    supabase = context["supabase"]
    return supabase.table("objectives").insert(obj.model_dump()).execute().data

@router.put("/{id}")
def update_objective(id: str, obj: Objective, context=Depends(user_supabase_client)):
    supabase = context["supabase"]
    return supabase.table("objectives").update(obj.model_dump()).eq("id", id).execute().data

@router.delete("/{id}")
def delete_objective(id: str, context=Depends(user_supabase_client)):
    supabase = context["supabase"]
    supabase.table("objectives").delete().eq("id", id).execute()
    return {"message": "Deleted"}
