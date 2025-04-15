from pydantic import BaseModel, UUID4
from typing import Optional, List
from openai import OpenAI
import os
import json


# ---------- Pydantic Models ----------

class TranscriptRequest(BaseModel):
    transcript: str

class ObjectiveProgress(BaseModel):
    trials_completed: int
    trials_total: int

class ParsedSession(BaseModel):
    student_name: str
    objective_description: str
    memo: str

class MatchStudent(BaseModel):
    id: str
    name: str
    similarity: float

class MatchObjective(BaseModel):
    id: str
    description: str
    similarity: float

class SuggestedSession(BaseModel):
    raw_input: str
    memo: str
    objective_progress: ObjectiveProgress
    student_suggestions: List[MatchStudent]
    objective_suggestions: List[MatchObjective]

class SuggestedSessions(BaseModel):
    sessions: List[SuggestedSession]


# ---------- LLM Prompt Utility ----------

def generate_llm_prompt(transcript: str) -> str:
    return f"""
You are an assistant that extracts structured session logs from a transcript for IEP progress tracking.

For each student mentioned in this transcript, extract:
- Student name (try to extract and write what you can most accurately infer as the name)
- Objective description (Mention the student's name in third person. Try to extract and write what you can most accurately infer as the objective description for the above student)
- Memo/summary of their progress (Mention the student's name in third person. Try to extract and write an accurate, comprehensive summary on the student's progress.)

If there is no meaningful session data in the transcript, return an empty list: []

Respond in JSON format like this:

[
  {{
    "student_name": "Johnny",
    "objective_description": "Johnny is working on solving word problems",
    "memo": " He solved 10 out of 15 problems correctly."

  }}
]

Transcript:
\"\"\"{transcript}\"\"\"
"""


# ---------- LLM Call ----------
def call_llm_extract_sessions(transcript: str) -> List[dict]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in environment variables")

    client = OpenAI(api_key=api_key)
    model = os.getenv("OPENAI_GPT_MODEL")
    prompt = generate_llm_prompt(transcript)

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You extract structured IEP session logs from transcripts."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
        )

        if not response.choices or not response.choices[0].message.content:
            raise RuntimeError("OpenAI returned an empty response")

        raw_output = response.choices[0].message.content.strip()

        if not raw_output:
            raise RuntimeError("OpenAI returned an empty string")

        try:
            parsed_output = json.loads(raw_output)
            print("transcript parser parsed_output: ", parsed_output, "for transcript: ", transcript)
            if not isinstance(parsed_output, list):
                raise RuntimeError("OpenAI response is not a list")
            return parsed_output
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse OpenAI response as JSON: {str(e)}\nResponse content: {raw_output}")

    except Exception as e:
        raise RuntimeError(f"OpenAI call failed: {str(e)}")


def infer_trials_completed(transcript: str, objective_type: str, target_accuracy: float) -> dict:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in environment variables")

    client = OpenAI(api_key=api_key)
    model = os.getenv("OPENAI_GPT_MODEL")
    system_prompt = (
        "You are an assistant that extracts objective progress data from session logs for IEP tracking.\n"
        "You will be given the session transcript, the type of objective (binary or trial), and the target accuracy if it's a trial.\n"
        "Respond ONLY with JSON of the following format:\n"
        "{\n"
        "  \"trials_completed\": <int>,\n"
        "  \"trials_total\": <int>\n"
        "}\n"
        "If objective_type is 'binary', set trials_completed and trials_total to 1 if the goal was met, otherwise 0.\n"
        "If objective_type is 'trial', try to infer the numerator and denominator from score references like percentages (e.g., 'scored 50%' = 50/100)."
    )

    user_prompt = f"""
Objective Type: {objective_type}
Target Accuracy: {target_accuracy}

Transcript:
\"\"\"{transcript}\"\"\"
"""

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,
        )

        content = response.choices[0].message.content.strip()
        print("🔎 trials inference raw output:", content)

        return json.loads(content)

    except Exception as e:
        print("❌ Error inferring trials:", e)
        return {
            "trials_completed": 0,
            "trials_total": 0
        }
    
# def standardize_objective_text(text: str) -> str:
#     api_key = os.getenv("OPENAI_API_KEY")
#     if not api_key:
#         raise ValueError("OPENAI_API_KEY not found in environment variables")

#     client = OpenAI(api_key=api_key)
#     model = os.getenv("OPENAI_GPT_MODEL")
#     prompt = f"Rewrite this IEP objective into a standardized, plain behavior-focused sentence: '{text}'"
#     response = client.chat.completions.create(
#             model=model,
#             messages=[
#                 {"role": "system", "content": "You are an assistant that standardizes IEP objective text into a plain, behavior-focused sentence."},
#                 {"role": "user", "content": prompt}
#             ],  
#             temperature=0.1,
#         )   
#     return response.choices[0].message.content.strip()
