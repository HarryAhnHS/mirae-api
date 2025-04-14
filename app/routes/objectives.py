from fastapi import APIRouter, Depends, HTTPException
from app.schemas.objective import CreateObjective
from app.dependencies.auth import user_supabase_client

router = APIRouter()

# -------- Objectives --------

@router.post("/objective")
def create_objective(obj: CreateObjective, context=Depends(user_supabase_client)):
    supabase = context["supabase"]
    user_id = context["user_id"]
    
    obj_dict = obj.model_dump()
    obj_dict["teacher_id"] = user_id
    
    # Convert UUID fields to strings
    obj_dict["goal_id"] = str(obj_dict["goal_id"])
    obj_dict["subject_area_id"] = str(obj_dict["subject_area_id"])

    response = supabase.table("objectives").insert(obj_dict).execute()
    return response.data

@router.get("/student/{student_id}")
def get_all_objectives(student_id: str, context=Depends(user_supabase_client)):
    supabase = context["supabase"]
    user_id = context["user_id"]
    
    response = supabase \
        .table("objectives") \
        .select("*") \
        .eq("teacher_id", user_id) \
        .eq("student_id", student_id) \
        .order("updated_at", desc=True) \
        .execute()
    return response.data

@router.get("/objective/{id}")
def get_objective(id: str, context=Depends(user_supabase_client)):
    supabase = context["supabase"]
    return supabase.table("objectives").select("*").eq("id", id).execute().data

@router.put("/objective/{id}")
def update_objective(id: str, obj: CreateObjective, context=Depends(user_supabase_client)):
    supabase = context["supabase"]
    user_id = context["user_id"]

    obj_dict = obj.model_dump()
    obj_dict["teacher_id"] = user_id

    # Convert UUID fields to strings
    obj_dict["goal_id"] = str(obj_dict["goal_id"])
    obj_dict["subject_area_id"] = str(obj_dict["subject_area_id"])

    return supabase.table("objectives").update(obj_dict).eq("id", id).execute().data

@router.delete("/objective/{id}")
def delete_objective(id: str, context=Depends(user_supabase_client)):
    supabase = context["supabase"]
    user_id = context["user_id"]

    # Verify objective belongs to the user
    existing_objective = supabase.table("objectives").select("*").eq("id", id).eq("teacher_id", user_id).execute()
    if not existing_objective.data:
        raise HTTPException(status_code=404, detail="Objective not found")    
    
    supabase.table("objectives").delete().eq("id", id).execute()
    return {"message": "Deleted"}