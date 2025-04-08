from fastapi import APIRouter, HTTPException, Depends
from app.schemas.student import Student, StudentCreate
from app.dependencies.auth import user_supabase_client

router = APIRouter()

@router.post("/student")
def create_student(student: StudentCreate, context=Depends(user_supabase_client)):
    supabase = context["supabase"]
    user_id = context["user_id"]

    print("user_id:", user_id)

    # Override teacher_id from context
    student_dict = student.model_dump()
    student_dict["teacher_id"] = user_id

    response = supabase.table("students").insert(student_dict).execute()
    
    return response.data

@router.get("/students")
def get_all_students(context=Depends(user_supabase_client)):
    supabase = context["supabase"]
    user_id = context["user_id"]

    response = supabase \
        .table("students") \
        .select("*, objectives(*)") \
        .eq("teacher_id", user_id) \
        .order("updated_at", desc=True) \
        .execute()
    
    print("response:", response)
    return response.data

@router.put("/student/{student_id}")
def update_student(student_id: str, student: Student, context=Depends(user_supabase_client)):
    supabase = context["supabase"]
    result = supabase.table("students").update(student.model_dump()).eq("id", student_id).execute()
    return result.data

@router.delete("/student/{student_id}")
def delete_student(student_id: str, context=Depends(user_supabase_client)   ):
    supabase = context["supabase"]
    result = supabase.table("students").delete().eq("id", student_id).execute()
    return {"message": "Student deleted", "status": result.status_code}
