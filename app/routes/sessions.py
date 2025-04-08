# app/routes/sessions.py
from fastapi import APIRouter, UploadFile, File, Form
from app.services.llm import transcribe_audio, summarize_note
from datetime import datetime
import uuid
from app.services.supabase import supabase

router = APIRouter()

@router.post("/transcribe_and_summarize")
async def transcribe_and_summarize(
    audio: UploadFile = File(...),
    objective_id: str = Form(...),
    prompt: str = Form(""),
):
    # 1. Read audio file bytes
    audio_bytes = await audio.read()

    # 2. Transcribe using Gemini
    transcription = await transcribe_audio(audio_bytes)

    # 3. Load previous logs for context (optional for now)
    # You can implement this using Supabase client if needed
    previous_logs = []

    # 4. Summarize + score
    summary_data = await summarize_note(transcription, prompt, previous_logs)

    # 5. Store in Supabase
    from app.services.supabase import supabase
    new_session = {
        "id": str(uuid.uuid4()),
        "objective_id": objective_id,
        "raw_input": transcription,
        "llm_summary": summary_data["summary"],
        "progress_delta": summary_data["progressDelta"],
        "date": datetime.utcnow().isoformat(),
        "created_at": datetime.utcnow().isoformat()
    }

    supabase.table("sessions").insert(new_session).execute()

    return summary_data
