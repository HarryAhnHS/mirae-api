import base64
import httpx
import os
import json

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GENAI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro-exp-03-25:generateContent"

async def transcribe_audio(audio_bytes: bytes) -> str:
    base64_audio = base64.b64encode(audio_bytes).decode("utf-8")
    payload = {
        "contents": [
            {"text": "Please transcribe this audio accurately."},
            {
                "inlineData": {
                    "mimeType": "audio/mpeg",
                    "data": base64_audio
                }
            }
        ]
    }

    async with httpx.AsyncClient() as client:
        res = await client.post(
            f"{GENAI_URL}?key={GEMINI_API_KEY}",
            json=payload
        )
    return res.json()["candidates"][0]["content"]["parts"][0]["text"]

async def summarize_note(note: str, prompt: str, previous_logs: list) -> dict:
    prompt_text = f"""
    Based on this progress note: "{note}"
    Custom Instructions: {prompt}
    Previous Context: {json.dumps(previous_logs, indent=2)}
    Please provide a JSON with 'summary' and 'progressDelta' fields only.
    """

    payload = {
        "contents": [{"text": prompt_text}]
    }

    async with httpx.AsyncClient() as client:
        res = await client.post(
            f"{GENAI_URL}?key={GEMINI_API_KEY}",
            json=payload
        )

    raw = res.json()["candidates"][0]["content"]["parts"][0]["text"]
    clean_json = raw.replace("```json", "").replace("```", "").strip()
    return json.loads(clean_json)
