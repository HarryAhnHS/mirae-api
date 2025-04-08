# app/routes/sessions.py
from fastapi import APIRouter, UploadFile, File, Form
from app.services.llm import transcribe_audio, summarize_note
from datetime import datetime, timezone
import uuid
from app.services.supabase import supabase

router = APIRouter()

@router.post("/transcribe")
async def transcribe(audio: UploadFile = File(...)):
    audio_bytes = await audio.read()
    transcription = await transcribe_audio(audio_bytes)
    return {"raw_text": transcription}

@router.post("/summarize_and_log")
async def summarize_and_log(
    raw_text: str = Form(...),
    objective_id: str = Form(...),
    prompt: str = Form(""),
):
    # 1. Fetch previous context if needed
    previous_logs = []

    # 2. Call LLM
    summary_data = await summarize_note(raw_text, prompt, previous_logs)

    # 3. Store in Supabase
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

