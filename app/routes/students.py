from fastapi import APIRouter, HTTPException
from app.services.supabase import supabase
from app.schemas.student import Student

router = APIRouter()

@router.post("/")
def create_student(student: Student):
    result = supabase.table("students").insert(student.dict()).execute()
    return result.data

@router.put("/{student_id}")
def update_student(student_id: str, student: Student):
    result = supabase.table("students").update(student.dict()).eq("id", student_id).execute()
    return result.data

@router.delete("/{student_id}")
def delete_student(student_id: str):
    result = supabase.table("students").delete().eq("id", student_id).execute()
    return {"message": "Student deleted", "status": result.status_code}
