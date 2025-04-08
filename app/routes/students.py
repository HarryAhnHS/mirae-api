from fastapi import APIRouter, HTTPException, Depends
from app.schemas.student import Student
from app.dependencies.auth import user_supabase_client

router = APIRouter()

@router.post("/")
def create_student(student: Student, context=Depends(user_supabase_client)):
    supabase = context["supabase"]
    result = supabase.table("students").insert(student.model_dump()).execute()
    return result.data

@router.put("/{student_id}")
def update_student(student_id: str, student: Student, context=Depends(user_supabase_client)):
    supabase = context["supabase"]
    result = supabase.table("students").update(student.model_dump()).eq("id", student_id).execute()
    return result.data

@router.delete("/{student_id}")
def delete_student(student_id: str, context=Depends(user_supabase_client)   ):
    supabase = context["supabase"]
    result = supabase.table("students").delete().eq("id", student_id).execute()
    return {"message": "Student deleted", "status": result.status_code}
