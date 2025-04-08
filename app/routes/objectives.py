from fastapi import APIRouter, Depends
from app.schemas.objective import Objective, SubjectArea, CreateSubjectArea
from app.dependencies.auth import user_supabase_client

router = APIRouter()

# -------- Subject Areas --------

@router.post("/subject-area")
def create_subject_area(subject: CreateSubjectArea, context=Depends(user_supabase_client)):
    supabase = context["supabase"]
    user_id = context["user_id"]
    
    # Override teacher_id from context
    subject_dict = subject.model_dump()
    subject_dict["teacher_id"] = user_id
    
    response = supabase.table("subject_areas").insert(subject_dict).execute()
    return response.data

@router.get("/subject-areas")
def get_all_subject_areas(context=Depends(user_supabase_client)):
    supabase = context["supabase"]
    user_id = context["user_id"]
    
    response = supabase \
        .table("subject_areas") \
        .select("*, objectives(*)") \
        .eq("teacher_id", user_id) \
        .order("updated_at", desc=True) \
        .execute()
    
    return response.data

@router.put("/subject-area/{id}")
def update_subject_area(id: str, subject: SubjectArea, context=Depends(user_supabase_client)):
    supabase = context["supabase"]
    return supabase.table("subject_areas").update(subject.model_dump()).eq("id", id).execute().data

@router.delete("/subject-area/{id}")
def delete_subject_area(id: str, context=Depends(user_supabase_client)):
    supabase = context["supabase"]
    supabase.table("subject_areas").delete().eq("id", id).execute()
    return {"message": "Deleted"}

# -------- Objectives --------

@router.post("/objective")
def create_objective(obj: Objective, context=Depends(user_supabase_client)):
    supabase = context["supabase"]
    user_id = context["user_id"]
    
    # Override teacher_id from context
    obj_dict = obj.model_dump()
    obj_dict["teacher_id"] = user_id
    
    response = supabase.table("objectives").insert(obj_dict).execute()
    return response.data

@router.put("/objective/{id}")
def update_objective(id: str, obj: Objective, context=Depends(user_supabase_client)):
    supabase = context["supabase"]
    return supabase.table("objectives").update(obj.model_dump()).eq("id", id).execute().data

@router.delete("/objective/{id}")
def delete_objective(id: str, context=Depends(user_supabase_client)):
    supabase = context["supabase"]
    supabase.table("objectives").delete().eq("id", id).execute()
    return {"message": "Deleted"}
