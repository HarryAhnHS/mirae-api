from fastapi import APIRouter, Body, Depends
from app.services.llm import analyze_session
from app.dependencies.auth import user_supabase_client
from datetime import datetime, timezone
from typing import List, Dict
from app.schemas.session import SessionCreate     
import uuid

router = APIRouter()

# -------- Summarize + Log Endpoint --------

@router.post("/analyze")
async def analyze(
    raw_text: str = Body(...),
    student: Dict = Body(...),
    objectives: List[Dict] = Body(...),
):
    # Build dynamic system prompt
    objective_summaries = "\n".join(
        [f"- {obj['id']}: {obj['description']}" for obj in objectives]
    )

    student_context = f"""
    You are analyzing a learning session log for a student named {student['name'].strip().title()}, 
    a Grade {student['grade_level']} student with {student.get('disability_type', 'no reported disabilities')}.
    The learning objectives for this session include:
    {objective_summaries}
    """

    full_prompt = f"""{student_context}
    Here is the raw session log from an educator:
    {raw_text}

    For each objective listed above, please generate a respective summary of the session and estimate the progress made towards the respective objective. 
    Return only a list of JSON objects with keys: "objective_id" (string), "summary" (string), and "progress_delta" (integer between -100 and 100 denoting percentage progress towards final objective).
    """

    # Call your LLM
    summary_data = await analyze_session(full_prompt)

    return summary_data

# -------- Create session --------
@router.post("/log")
def log(
    session: SessionCreate,
    context=Depends(user_supabase_client)
):
    supabase = context["supabase"]
    user_id = context["user_id"]

    new_session = {
        "id": str(uuid.uuid4()),
        "teacher_id": user_id,
        "student_id": session.student_id,
        "objective_id": session.objective_id,
        "raw_input": session.raw_input,
        "llm_summary": session.llm_summary,
        "progress_delta": session.progress_delta,
        "date": datetime.now(timezone.utc).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }

    supabase.table("sessions").insert(new_session).execute()

    return {"status": "success", "session_id": new_session["id"]}

# -------- Get All Sessions from logged in user --------
@router.get("/sessions")
async def get_all_sessions(context=Depends(user_supabase_client)):
    supabase = context["supabase"]
    user_id = context["user_id"]

    response = supabase \
        .from_("sessions") \
        .select("""
            *,
            student:students (
                id, name, grade_level, disability_type
            ),
            objective:objectives (
                id, description, current_progress, weekly_frequency,
                subject_area:subject_areas (
                    id, name
                )
            )
        """) \
        .eq("teacher_id", user_id) \
        .order("created_at", desc=True) \
        .execute()

    return response.data

# -------- Get session by id --------
@router.get("/sessions/{session_id}")
def get_session_by_id(session_id: str, context=Depends(user_supabase_client)):
    supabase = context["supabase"]

    response = supabase.table("sessions").select("""
        *,
            student:students (
                id, name, grade_level, disability_type
            ),
            objective:objectives (
                id, description, current_progress, weekly_frequency,
                subject_area:subject_areas (
                    id, name
                )
            )
        """).eq("id", session_id).execute()
    return response.data

# -------- Edit session --------
@router.put("/sessions/{session_id}")
def edit_session(session_id: str, session: SessionCreate, context=Depends(user_supabase_client)):
    supabase = context["supabase"]
    response = supabase.table("sessions").update(session.model_dump()).eq("id", session_id).execute()
    return response.data


@router.get("/sessions/student/{student_id}")
def get_sessions_by_student(student_id: str, context=Depends(user_supabase_client)):
    supabase = context["supabase"]
    user_id = context["user_id"]
    return supabase \
        .table("sessions") \
        .select("*") \
        .eq("teacher_id", user_id) \
        .eq("student_id", student_id) \
        .order("created_at", desc=True) \
        .execute().data

@router.get("/sessions/objective/{objective_id}")
def get_sessions_by_objective(objective_id: str, context=Depends(user_supabase_client)):
    supabase = context["supabase"]
    user_id = context["user_id"]
    return supabase \
        .table("sessions") \
        .select("*") \
        .eq("teacher_id", user_id) \
        .eq("objective_id", objective_id) \
        .order("created_at", desc=True) \
        .execute().data

