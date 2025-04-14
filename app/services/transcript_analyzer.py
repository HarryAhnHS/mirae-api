from pydantic import BaseModel, UUID4, Field
from typing import Optional, List
import json
import os
from openai import OpenAI

class ObjectiveProgress(BaseModel):
    trials_completed: Optional[int]
    trials_total: Optional[int]

class ParsedSession(BaseModel):
    student_name: str
    objective_title: str
    objective_progress: Optional[ObjectiveProgress]
    memo: Optional[str]
    raw_input: str

class FinalSessionLog(BaseModel):
    student_id: UUID4
    objective_id: UUID4
    objective_progress: Optional[ObjectiveProgress]
    memo: Optional[str]
    raw_input: str

class FinalSessionLogs(BaseModel):
    sessions: List[FinalSessionLog]

def generate_llm_prompt(transcript: str) -> str:
    return f"""
You are an assistant that extracts structured session logs from a transcript for IEP progress tracking.

For each student mentioned in this transcript, extract:
- Student name
- Objective title
- Trials completed (if mentioned)
- Total trials (if mentioned)
- Memo/summary of their progress

Respond in JSON format like this:

[
  {{
    "student_name": "Johnny",
    "objective_title": "Solving word problems",
    "objective_progress": {{
      "trials_completed": 3,
      "trials_total": 5
    }},
    "memo": "Did well"
  }}
]

Transcript:
\"\"\"{transcript}\"\"\"
"""

async def resolve_ids(supabase, teacher_id: str, student_name: str, objective_title: str):
    student = (
        supabase.table("students")
        .select("id")
        .eq("teacher_id", teacher_id)
        .ilike("name", student_name.strip())
        .execute()
    )
    if not student.data:
        raise ValueError(f"Student '{student_name}' not found")
    student_id = student.data[0]["id"]

    objective = (
        supabase.table("objectives")
        .select("id")
        .eq("teacher_id", teacher_id)
        .ilike("title", objective_title.strip())
        .execute()
    )
    if not objective.data:
        raise ValueError(f"Objective '{objective_title}' not found")
    objective_id = objective.data[0]["id"]

    return student_id, objective_id


def call_llm_extract_sessions(transcript: str, model_name: str = "gpt-4-0125-preview") -> List[dict]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in environment variables")

    client = OpenAI(api_key=api_key)

    prompt = generate_llm_prompt(transcript)

    try:
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_GPT_MODEL") or model_name,
            messages=[
                {"role": "system", "content": "You extract structured IEP session logs from transcripts."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
        )
        raw_output = response.choices[0].message.content.strip()

        # Validate and return as JSON
        return json.loads(raw_output)

    except Exception as e:
        raise RuntimeError(f"OpenAI call failed: {str(e)}")
