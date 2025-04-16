from fastapi import APIRouter, Depends, HTTPException
from app.schemas.subject_area import SubjectArea, CreateSubjectArea
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
        .select("*, objective:objectives(*, student:students(*),  goal:goals(*))") \
        .eq("teacher_id", user_id) \
        .order("updated_at", desc=True) \
        .execute()
    
    return response.data

# Get subject areas for a single student
@router.get("/student/{student_id}")
def get_subject_areas_by_student(student_id: str, context=Depends(user_supabase_client)):
    supabase = context["supabase"]
    user_id = context["user_id"]

    response = supabase \
        .table("subject_areas") \
        .select("*, objective:objectives!inner(*, student:students(*), goal:goals(*))") \
        .eq("teacher_id", user_id) \
        .eq("objectives.student_id", student_id) \
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
    user_id = context["user_id"]

    # Verify subject area belongs to the user
    existing_subject_area = supabase.table("subject_areas").select("*").eq("id", id).eq("teacher_id", user_id).execute()
    if not existing_subject_area.data:
        raise HTTPException(status_code=404, detail="Subject area not found")
    
    supabase.table("subject_areas").delete().eq("id", id).execute()
    return {"message": "Deleted"}