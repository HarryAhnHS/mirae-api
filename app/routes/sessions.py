from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from app.services.llm import transcribe_audio, summarize_note
from app.dependencies.auth import user_supabase_client
from datetime import datetime, timezone
import uuid

router = APIRouter()

# -------- Transcription Endpoint --------

@router.post("/transcribe")
async def transcribe(
    audio: UploadFile = File(...),
    context=Depends(user_supabase_client)
):
    audio_bytes = await audio.read()
    transcription = await transcribe_audio(audio_bytes)
    return {"raw_text": transcription}


# -------- Summarize + Log Endpoint --------

@router.post("/summarize_and_log")
async def summarize_and_log(
    raw_text: str = Form(...),
    objective_id: str = Form(...),
    prompt: str = Form(""),
    context=Depends(user_supabase_client)
):
    supabase = context["supabase"]
    user_id = context["user_id"]

    # Optional: fetch previous logs for context (not implemented yet)
    previous_logs = []

    # Summarize using LLM
    summary_data = await summarize_note(raw_text, prompt, previous_logs)

    # Create session record
    new_session = {
        "id": str(uuid.uuid4()),
        "objective_id": objective_id,
        "raw_input": raw_text,
        "llm_summary": summary_data["summary"],
        "progress_delta": summary_data["progressDelta"],
        "date": datetime.now(timezone.utc).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }

    supabase.table("sessions").insert(new_session).execute()

    return summary_data

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
