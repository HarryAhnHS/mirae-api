from fastapi import APIRouter, Depends
from app.schemas.goal import CreateGoal
from app.dependencies.auth import user_supabase_client

router = APIRouter()

@router.post("/goal")
def create_goal(goal: CreateGoal, context=Depends(user_supabase_client)):
    supabase = context["supabase"]
    user_id = context["user_id"]
    goal_data = goal.model_dump()
    goal_data["teacher_id"] = user_id
    return supabase.table("goals").insert(goal_data).execute().data

@router.get("/student/{student_id}/subject-area/{subject_area_id}")
def get_goals_for_student_and_subject_area(subject_area_id: str, student_id: str, context=Depends(user_supabase_client)):
    supabase = context["supabase"]
    user_id = context["user_id"]

    response = supabase \
        .table("goals") \
        .select("*, subject_area:subject_areas(name), objectives(*)") \
        .eq("teacher_id", user_id) \
        .eq("subject_area_id", subject_area_id) \
        .eq("student_id", student_id) \
        .order("updated_at", desc=True) \
        .execute()
    return response.data

@router.get("/goal/{goal_id}")
def get_goal(goal_id: str, context=Depends(user_supabase_client)):
    supabase = context["supabase"]
    return supabase.table("goals").select("*").eq("id", goal_id).execute().data

@router.put("/goal/{goal_id}")
def update_goal(goal_id: str, goal: CreateGoal, context=Depends(user_supabase_client)):
    supabase = context["supabase"]
    return supabase.table("goals").update(goal.model_dump()).eq("id", goal_id).execute().data

@router.delete("/goal/{goal_id}")
def delete_goal(goal_id: str, context=Depends(user_supabase_client)):
    supabase = context["supabase"]
    supabase.table("goals").delete().eq("id", goal_id).execute()
    return {"message": "Deleted"}
