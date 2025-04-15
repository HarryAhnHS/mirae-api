from pydantic import BaseModel
from typing import List
# from openai import OpenAI
from together import Together

import os
import json

from dotenv import load_dotenv
load_dotenv()


# ---------- Pydantic Models ----------
class Goal(BaseModel):
    id: str
    title: str

class SubjectArea(BaseModel):
    id: str
    name: str

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
    queried_objective_description: str

class SuggestedSession(BaseModel):
    raw_input: str
    memo: str
    objective_progress: ObjectiveProgress
    student_suggestions: List[MatchStudent]
    objective_suggestions: List[MatchObjective]

client = Together(api_key=os.getenv("TOGETHER_API_KEY")) # auth defaults to env TOGETHER_API_KEY
model = os.getenv("TOGETHER_MODEL", "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free")

# ---------- LLM Calls ----------
def call_llm_extract_sessions(transcript: str) -> List[dict]:
    prompt = f"""
        You are an assistant that extracts structured session logs from a transcript for IEP progress tracking.
        Your job is to split the transcript into individual *sessions*, not by student but by **distinct activities or observations**. Each session should represent a unique event or evaluation for a single student.
        Each session may mention the same student or same objective more than once, but you must create a **separate log per activity or observation**, even if it's for the same student.

        For each session, extract:
        - `student_name`: The name of the student the session is about
        - `objective_description`: Describe what the student was working on, in third person
        - `memo`: Summarize their performance or outcome for this specific session, in third person

        🛑 Do **NOT** combine different sessions into one JSON object, even if the same student/objective is involved.

        If there is no meaningful session data in the transcript, return an empty list: []

        Respond ONLY in valid JSON list format, like this:
        [
        {{
            "student_name": "Johnny",
            "objective_description": "Johnny is working on solving word problems.",
            "memo": "Johnny solved 10 out of 15 problems correctly."
        }},
        ]

        Transcript:
        \"\"\"{transcript}\"\"\"
        """

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
            if not isinstance(parsed_output, list):
                raise RuntimeError("OpenAI response is not a list")
            return parsed_output
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse OpenAI response as JSON: {str(e)}\nResponse content: {raw_output}")

    except Exception as e:
        raise RuntimeError(f"OpenAI call failed: {str(e)}")


def infer_trials_completed(
    transcript: str, 
    objective_description: str,
    objective_student_name: str,
    objective_type: str, 
    target_accuracy: float
) -> dict:
    system_prompt = (
        "You are an assistant that extracts objective progress data from session logs for IEP tracking.\n"
        "You will be given the session transcript, objective details, and type information.\n"
        "Respond ONLY with JSON of the following format:\n"
        "{\n"
        "  \"trials_completed\": <int>,\n"
        "  \"trials_total\": <int>\n"
        "}\n"
        "If objective_type is 'binary', set trials_completed and trials_total to 1 if the goal was met, otherwise 0.\n"
        "If objective_type is 'trial', try to infer the numerator and denominator from score references like percentages (e.g., 'scored 50%' = 50/100). If you can't infer the numerator and denominator, default to 100 as trials_total and infer trials_completed based on the transcript and target_accuracy."
    )

    user_prompt = f"""
        Student: {objective_student_name}
        Objective: {objective_description}
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

        return json.loads(content)

    except Exception as e:
        print("❌ Error inferring trials:", e)
        return {
            "trials_completed": 0,
            "trials_total": 0
        }