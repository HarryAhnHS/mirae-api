from fastapi import APIRouter, Body, Depends, HTTPException
# from app.services.llm import analyze_session
from app.dependencies.auth import user_supabase_client
from datetime import datetime, timezone
from typing import List, Dict
from app.schemas.session import SessionsWithProgressCreate, SessionCreate
import uuid

router = APIRouter()

# -------- Summarize + Log Endpoint --------

# @router.post("/analyze")
# async def analyze(
#     raw_text: str = Body(...),
#     student: Dict = Body(...),
#     objectives: List[Dict] = Body(...),
# ):
#     # Build dynamic system prompt
#     objective_summaries = "\n".join(
#         [f"- {obj['id']}: {obj['description']}" for obj in objectives]
#     )

#     student_context = f"""
#     You are analyzing a learning session log for a student named {student['name'].strip().title()}, 
#     a Grade {student['grade_level']} student with {student.get('disability_type', 'no reported disabilities')}.
#     The learning objectives for this session include:
#     {objective_summaries}
#     """

#     full_prompt = f"""{student_context}
#     Here is the raw session log from an educator:
#     {raw_text}

#     For each objective listed above, please generate a respective summary of the session and estimate the progress made towards the respective objective. 
#     Return only a list of JSON objects with keys: "objective_id" (string), "summary" (string), and "progress_delta" (integer between -100 and 100 denoting percentage progress towards final objective).
#     """

#     # Call your LLM
#     summary_data = await analyze_session(full_prompt)

#     return summary_data

# -------- Create session --------
# @router.post("/log")
# def log(
#     sessions: SessionsWithProgressCreate,
#     context=Depends(user_supabase_client)
# ):
#     supabase = context["supabase"]
    
#     # Process each session in the array
#     for session_data in sessions.sessions:
#         # Create session record
#         session_result = supabase.table("sessions").insert({
#             "id": str(uuid.uuid4()),
#             "student_id": session_data.student_id,
#             "educator_id": session_data.educator_id,
#             "date": session_data.date,
#             "duration_minutes": session_data.duration_minutes,
#             "notes": session_data.notes,
#             "created_at": datetime.now(timezone.utc).isoformat()
#         }).execute()
        
#         session_id = session_result.data[0]["id"]
        
#         # Create progress records for each objective
#         for progress in session_data.progress:
#             supabase.table("session_progress").insert({
#                 "id": str(uuid.uuid4()),
#                 "session_id": session_id,
#                 "objective_id": progress.objective_id,
#                 "progress_delta": progress.progress_delta,
#                 "summary": progress.summary,
#                 "created_at": datetime.now(timezone.utc).isoformat()
#             }).execute()
    
#     return {"message": "Sessions logged successfully"}

# -------- Get All Sessions from logged in user --------
@router.get("/sessions")
async def get_all_sessions(context=Depends(user_supabase_client)):
    supabase = context["supabase"]
    user_id = context["user_id"]

    response = supabase \
    .from_("sessions") \
    .select("""
        *,
        student:students(*),
        objective:objectives(
            *,
            subject_area:subject_areas(id, name),
            goal:goals(id, title)
        ),
        objective_progress:objective_progress(*)
    """) \
    .eq("teacher_id", user_id) \
    .order("created_at", desc=True) \
    .execute()


    return response.data

@router.get("/recent")
async def get_recent_sessions(context=Depends(user_supabase_client)):
    supabase = context["supabase"]
    user_id = context["user_id"]

    response = supabase.table("sessions").select("*").eq("teacher_id", user_id).order("created_at", desc=True).limit(10).execute()
    return response.data

# -------- Edit session --------
@router.put("/{session_id}")
def edit_session_and_progress(
    session_id: str,
    payload: dict = Body(...),
    context=Depends(user_supabase_client)
):
    supabase = context["supabase"]
    user_id = context["user_id"]
    
    # Verify session belongs to the user
    existing_session = supabase.table("sessions").select("*").eq("id", session_id).eq("teacher_id", user_id).execute()
    if not existing_session.data:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get the objective_progress_id from the existing session
    objective_progress_id = existing_session.data[0]["objective_progress_id"]
    
    # Update the session record
    updated_session = supabase.table("sessions").update({
        "student_id": payload["student_id"],
        "objective_id": payload["objective_id"],
        "memo": payload["memo"],
        "created_at": payload["created_at"]
    }).eq("id", session_id).execute()
    
    # Update the associated objective_progress record
    updated_progress = supabase.table("objective_progress").update({
        "trials_completed": payload["objective_progress"]["trials_completed"],
        "trials_total": payload["objective_progress"]["trials_total"]
    }).eq("id", objective_progress_id).execute()
    
    return {
        "session": updated_session.data[0],
        "progress": updated_progress.data[0]
    }

# -------- Delete session --------
@router.delete("/{session_id}")
def delete_session(
    session_id: str,
    context=Depends(user_supabase_client)
):
    supabase = context["supabase"]
    user_id = context["user_id"]
    
    # Verify session belongs to the user
    existing_session = supabase.table("sessions").select("*").eq("id", session_id).eq("teacher_id", user_id).execute()
    if not existing_session.data:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Delete the session
    supabase.table("sessions").delete().eq("id", session_id).execute()
    
    return {"message": "Session deleted successfully"}

# -------- Get all sessions by student --------
@router.get("/student/{student_id}")
def get_sessions_by_student(
    student_id: str,
    context=Depends(user_supabase_client)
):
    supabase = context["supabase"]
    user_id = context["user_id"]
    
    response = supabase.table("sessions") \
    .select("""
        *,
        student:students(*),
        objective:objectives(
            *,
            subject_area:subject_areas(id, name),
            goal:goals(id, title)
        ),
        objective_progress:objective_progress(*)
    """) \
    .eq("teacher_id", user_id) \
    .eq("student_id", student_id) \
    .order("created_at", desc=True) \
    .execute()
    
    return response.data

# -------- Get all sessions by objective --------
@router.get("/objective/{objective_id}")
def get_sessions_by_objective(
    objective_id: str,
    context=Depends(user_supabase_client)
):
    supabase = context["supabase"]
    user_id = context["user_id"]
    
    response = supabase.table("sessions") \
    .select("""
        *,
        student:students(*),
        objective:objectives(
            *,
            subject_area:subject_areas(id, name),
            goal:goals(id, title)
        ),
        objective_progress:objective_progress(*)
    """) \
    .eq("teacher_id", user_id) \
    .eq("objective_id", objective_id) \
    .order("created_at", desc=True) \
    .execute()
    
    return response.data

# -------- Log session and progress --------
@router.post("/session/log")
def log_session_and_progress(
    sessions: SessionsWithProgressCreate,
    context=Depends(user_supabase_client)
):
    supabase = context["supabase"]
    user_id = context["user_id"]

    session_ids = []

    for session in sessions.root:
        session_id = str(uuid.uuid4())
        objective_progress_id = str(uuid.uuid4())

        # Insert into objective_progress
        progress_payload = {
            "id": objective_progress_id,
            "teacher_id": user_id,
            "student_id": session.student_id,
            "objective_id": session.objective_id,
            "trials_completed": session.objective_progress.trials_completed,
            "trials_total": session.objective_progress.trials_total,
        }

        supabase.table("objective_progress").insert(progress_payload).execute()

        # Insert into sessions
        session_payload = {
            "id": session_id,
            "student_id": session.student_id,
            "teacher_id": user_id,
            "objective_id": session.objective_id,
            "memo": session.memo,
            "created_at": session.created_at,
            "objective_progress_id": objective_progress_id
        }

        supabase.table("sessions").insert(session_payload).execute()
        session_ids.append(session_id)

    return {
        "status": "success",
        "session_ids": session_ids
    }
