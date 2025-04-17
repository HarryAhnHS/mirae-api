import os
import json
from pathlib import Path
from typing import List, Dict, Any
from pydantic import BaseModel, Field, ValidationError
from openai import OpenAI
import pdfplumber
from tempfile import NamedTemporaryFile
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Objective(BaseModel):
    description: str = Field(..., description="Verbatim text for the objective.")

class AnnualGoal(BaseModel):
    goal_description: str = Field(
        ...,
        description="Verbatim text describing the annual goal."
    )
    objectives: List[Objective] = Field(
        ...,
        description="Objectives that support this annual goal."
    )

class AreaOfNeed(BaseModel):
    area_name: str = Field(
        ...,
        description="Verbatim text for the area/subject (e.g. Math, Reading)."
    )
    goals: List[AnnualGoal] = Field(
        ...,
        description="A list of goals in this area."
    )

class IEP(BaseModel):
    student_name: str = Field(..., description="Full name of the student.")
    disability_type: str = Field(..., description="Primary disability or eligibility.")
    grade_level: str = Field(..., description="Grade level, e.g. 'Grade 5'.")
    areas_of_need: List[AreaOfNeed] = Field(
        ...,
        description="List of subject areas, each containing goals with objectives."
    )

    class Config:
        extra = "allow"

def clean_model_output(candidate: dict) -> dict:
    cleaned = dict(candidate)

    for fld in ["student_name", "disability_type", "grade_level"]:
        if fld not in cleaned or not isinstance(cleaned[fld], str):
            cleaned[fld] = "Unknown"

    if "areas_of_need" not in cleaned or not isinstance(cleaned["areas_of_need"], list):
        cleaned["areas_of_need"] = []
    
    for i, area in enumerate(cleaned["areas_of_need"]):
        if not isinstance(area, dict):
            cleaned["areas_of_need"][i] = {
                "area_name": "No area of need detected",
                "goals": []
            }
            continue
        
        if "area_name" not in area or not isinstance(area["area_name"], str):
            area["area_name"] = "No area of need detected"
        if "goals" not in area or not isinstance(area["goals"], list):
            area["goals"] = []

        for j, goal in enumerate(area["goals"]):
            if not isinstance(goal, dict):
                area["goals"][j] = {
                    "goal_description": "No goal detected",
                    "objectives": []
                }
                continue
            
            if "goal_description" not in goal or not isinstance(goal["goal_description"], str):
                goal["goal_description"] = "No goal detected"
            if "objectives" not in goal or not isinstance(goal["objectives"], list):
                goal["objectives"] = []

            for k, obj in enumerate(goal["objectives"]):
                if not isinstance(obj, dict):
                    goal["objectives"][k] = {"description": "Unknown"}
                    continue

                desc = obj.get("description", "Unknown")
                if not isinstance(desc, str):
                    desc = "Unknown"

                goal["objectives"][k] = {"description": desc}

    return cleaned

class IEPParser:
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        
        self.client = OpenAI(api_key=api_key)
        
        # Use gpt-4o-mini explicitly
        self.model_name = "gpt-4o-mini"
        logger.info(f"Using OpenAI model: {self.model_name}")

    def extract_text_from_pdf_bytes(self, pdf_bytes: bytes) -> str:
        """Extract text from PDF bytes."""
        text_chunks = []
        
        with NamedTemporaryFile(suffix='.pdf', delete=True) as tmp_file:
            tmp_file.write(pdf_bytes)
            tmp_file.flush()
            
            try:
                with pdfplumber.open(tmp_file.name) as pdf:
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text_chunks.append(page_text)
            except Exception as e:
                logger.error(f"Error extracting text from PDF: {str(e)}")
                raise RuntimeError(f"Error extracting text from PDF: {str(e)}")

        return "\n".join(text_chunks)

    def get_raw_response(self, text: str) -> str:
        instructions = (
            "You are parsing an IEP. Return valid JSON with these fields:\n"
            "1) student_name (string)\n"
            "2) disability_type (string)\n"
            "3) grade_level (string)\n"
            "4) areas_of_need (array). Each area_of_need:\n"
            "    - area_name (string, e.g. 'Math', 'Reading')\n"
            "    - goals (array). Each goal:\n"
            "        * goal_description (string)\n"
            "        * objectives (array). Each objective:\n"
            "            + description (string, verbatim)\n\n"
            "Rules:\n"
            "- If you can't find a value, use 'Unknown' or empty lists.\n"
            "- Do not omit any required fields.\n"
            "- Return ONLY valid JSON. No markdown or extra text.\n"
            "- Capture area of need, goals, and objectives exactly as they appear."
        )

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": instructions},
                    {"role": "user", "content": f"IEP Text:\n{text}"}
                ],
                temperature=0.3
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Error calling OpenAI API: {str(e)}")
            raise RuntimeError(f"Error calling OpenAI API: {str(e)}")

    async def parse_iep_from_pdf(self, pdf_bytes: bytes) -> IEP:
        """Parse IEP data from PDF bytes."""
        try:
            text = self.extract_text_from_pdf_bytes(pdf_bytes)
            logger.info(f"Extracted {len(text)} characters from PDF")
            
            raw_response = self.get_raw_response(text)
            logger.info("Received response from OpenAI")
            
            try:
                parsed_json = json.loads(raw_response)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON returned from model: {raw_response[:100]}...")
                raise ValueError(f"Invalid JSON returned from model: {str(e)}")

            cleaned_data = clean_model_output(parsed_json)
            iep_obj = IEP(**cleaned_data)
            return iep_obj
        except Exception as e:
            logger.error(f"Error parsing IEP: {str(e)}")
            raise 