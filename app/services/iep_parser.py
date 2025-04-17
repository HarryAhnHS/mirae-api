import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ValidationError
from openai import OpenAI
import pdfplumber
from tempfile import NamedTemporaryFile
import logging
from app.services.objective_parser import parse_objective

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Objective(BaseModel):
    description: str = Field(..., description="Verbatim text for the objective.")
    objective_type: Optional[str] = Field(None, description="Type of objective (trials, binary, rubric, continuous)")
    target_accuracy: Optional[float] = Field(None, description="Target accuracy percentage as decimal (e.g., 80.0)")
    target_consistency_trials: Optional[int] = Field(None, description="Total number of trials for consistency measurement")
    target_consistency_successes: Optional[int] = Field(None, description="Target number of successful trials")
    reporting_frequency: Optional[str] = Field(None, description="How often progress is reported")
    
    class Config:
        extra = "ignore"  # Ignore extra fields that aren't in the model

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
    """
    Clean and process the data from the LLM to ensure it meets expected format.
    More lenient with missing data to prevent validation errors.
    """
    try:
        cleaned = dict(candidate)

        # Ensure required string fields exist
        for fld in ["student_name", "disability_type", "grade_level"]:
            if fld not in cleaned or not isinstance(cleaned[fld], str):
                cleaned[fld] = "Unknown"

        # Ensure areas_of_need is a list
        if "areas_of_need" not in cleaned or not isinstance(cleaned["areas_of_need"], list):
            cleaned["areas_of_need"] = []
        
        # Process each area of need
        for i, area in enumerate(cleaned["areas_of_need"]):
            # Ensure area is a dict
            if not isinstance(area, dict):
                cleaned["areas_of_need"][i] = {
                    "area_name": "Unknown",
                    "goals": []
                }
                continue
            
            # Ensure area_name is a string
            if "area_name" not in area or not isinstance(area["area_name"], str):
                area["area_name"] = "Unknown"
            
            # Ensure goals is a list
            if "goals" not in area or not isinstance(area["goals"], list):
                area["goals"] = []

            # Process each goal
            for j, goal in enumerate(area["goals"]):
                # Ensure goal is a dict
                if not isinstance(goal, dict):
                    area["goals"][j] = {
                        "goal_description": "Unknown",
                        "objectives": []
                    }
                    continue
                
                # Ensure goal_description is a string
                if "goal_description" not in goal or not isinstance(goal["goal_description"], str):
                    goal["goal_description"] = "Unknown"
                
                # Ensure objectives is a list
                if "objectives" not in goal or not isinstance(goal["objectives"], list):
                    goal["objectives"] = []

                # Process each objective
                for k, obj in enumerate(goal["objectives"]):
                    # Ensure objective is a dict with at least a description
                    if not isinstance(obj, dict):
                        goal["objectives"][k] = {"description": "Unknown"}
                        continue
                    
                    # Ensure description exists and is a string
                    if "description" not in obj or not isinstance(obj["description"], str):
                        obj["description"] = "Unknown"
                    
                    # Parse the objective to extract additional fields
                    if obj["description"] != "Unknown":
                        try:
                            parsed_objective = parse_objective(obj["description"])
                            goal["objectives"][k] = parsed_objective
                        except Exception as e:
                            logger.warning(f"Error parsing objective: {str(e)}")
                            # If parsing fails, keep at least the description
                            goal["objectives"][k] = {"description": obj["description"]}
                    else:
                        goal["objectives"][k] = {"description": "Unknown"}

        return cleaned
    except Exception as e:
        # If anything fails in cleaning, log it and return the original data
        # with minimal required fields to prevent validation errors
        logger.error(f"Error in clean_model_output: {str(e)}")
        return {
            "student_name": "Unknown",
            "disability_type": "Unknown",
            "grade_level": "Unknown",
            "areas_of_need": []
        }

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