from fastapi import APIRouter, Body, Depends, HTTPException
# from app.services.llm import analyze_session
from app.dependencies.auth import user_supabase_client
from datetime import datetime, timezone
from typing import List, Dict
from app.schemas.session import SessionsWithProgressCreate, SessionCreate
import uuid
from app.services.student_summarizer import generate_and_store_student_summary
router = APIRouter()

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

    summary = generate_and_store_student_summary(supabase, payload["student_id"], user_id)
    print(f"onEdit: ✅ Successfully generated and stored student summary: {summary}")
    
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

    summary = generate_and_store_student_summary(supabase, existing_session.data[0]["student_id"], user_id)
    print(f"onDelete: ✅ Successfully updated student summary: {summary}")
    
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

        summary = generate_and_store_student_summary(supabase, session.student_id, user_id)
        print(f"onLog: ✅ Successfully generated and stored student summary: {summary}")

    return {
        "status": "success",
        "session_ids": session_ids
    }
