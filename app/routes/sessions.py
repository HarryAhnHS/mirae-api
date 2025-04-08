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
        [f"- {obj['description']}" for obj in objectives]
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

    Please generate a summary of the session and estimate the progress made across the objectives above. 
    Return only a JSON with keys: "summary" (string) and "progress_delta" (integer between -100 and 100 denoting percentage progress towards final objective).
    """

    # Call your LLM
    summary_data = await analyze_session(full_prompt)

    return summary_data

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

@router.get("/")
async def get_all_sessions(context=Depends(user_supabase_client)):
    supabase = context["supabase"]
    user_id = context["user_id"]

    # Join sessions → objectives → goals → subject_areas
    # Also join sessions → students directly
    response = supabase \
        .from_("sessions") \
        .select("""...""") \
        .eq("teacher_id", user_id) \
        .order("created_at", desc=True) \
        .execute()

    sessions = response.data
    return sessions
