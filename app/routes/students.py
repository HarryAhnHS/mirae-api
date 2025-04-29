from fastapi import APIRouter, HTTPException, Depends
from app.schemas.student import Student, StudentCreate
from app.dependencies.auth import user_supabase_client
from app.services.student_summarizer import call_llm_student_summary

router = APIRouter()

# Get all students
@router.get("/students")
def get_all_students(context=Depends(user_supabase_client)):
    supabase = context["supabase"]
    user_id = context["user_id"]

    response = supabase \
        .table("students") \
        .select("""
            *,
            objectives (
                *,
                subject_area:subject_areas (
                    id,
                    name
                ),
                goal:goals (
                    id,
                    title
                )
            )
        """) \
        .eq("teacher_id", user_id) \
        .order("updated_at", desc=True) \
        .execute()
    return response.data

# Get single student by id
@router.get("/student/{student_id}")
def get_student_by_id(student_id: str, context=Depends(user_supabase_client)):
    supabase = context["supabase"]
    return supabase \
        .table("students") \
        .select("*, objectives(*)") \
        .eq("id", student_id) \
        .execute().data

# Create student
@router.post("/student")
def create_student(student: StudentCreate, context=Depends(user_supabase_client)):
    supabase = context["supabase"]
    user_id = context["user_id"]

    # Override teacher_id from context
    student_dict = student.model_dump()
    student_dict["teacher_id"] = user_id

    response = supabase.table("students").insert(student_dict).execute()
    
    return response.data


# Edit student
@router.put("/student/{student_id}")
def update_student(student_id: str, student: StudentCreate, context=Depends(user_supabase_client)):
    supabase = context["supabase"]
    user_id = context["user_id"]

    # Override teacher_id from context
    student_dict = student.model_dump()
    student_dict["teacher_id"] = user_id

    response = supabase.table("students").update(student_dict).eq("id", student_id).execute()
    return response.data

# Delete student
@router.delete("/student/{student_id}")
def delete_student(student_id: str, context=Depends(user_supabase_client)   ):
    supabase = context["supabase"]
    user_id = context["user_id"]

    # Verify student belongs to the user
    existing_student = supabase.table("students").select("*").eq("id", student_id).eq("teacher_id", user_id).execute()
    if not existing_student.data:
        raise HTTPException(status_code=404, detail="Student not found")    
    
    response = supabase.table("students").delete().eq("id", student_id).execute()
    return response.data