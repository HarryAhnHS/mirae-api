from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Security, Body
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.dependencies.auth import user_supabase_client
from app.services.iep_parser import IEPParser
from app.schemas.student import StudentCreate
from typing import Dict, List, Optional
from pydantic import BaseModel
import uuid
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()
security = HTTPBearer()

class ObjectiveData(BaseModel):
    description: str

class GoalData(BaseModel):
    goal_description: str
    objectives: List[ObjectiveData]

class AreaOfNeedData(BaseModel):
    area_name: str
    goals: List[GoalData]

class IEPData(BaseModel):
    student_name: str
    disability_type: str
    grade_level: str
    areas_of_need: List[AreaOfNeedData]

@router.post("/parse", 
    summary="Parse IEP PDF",
    description="Upload and parse an IEP PDF file to preview the data before saving.",
    response_model=IEPData
)
async def parse_iep(
    file: UploadFile = File(...),
    credentials: HTTPAuthorizationCredentials = Security(security),
    context=Depends(user_supabase_client)
):
    """
    Parse an IEP PDF and return the structured data for preview.
    """
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    try:
        logger.info(f"Received file {file.filename} for parsing")
        
        # Read the PDF file
        pdf_bytes = await file.read()
        logger.info(f"Read {len(pdf_bytes)} bytes from uploaded PDF")
        
        # Parse the IEP
        try:
            parser = IEPParser()
            iep_data = await parser.parse_iep_from_pdf(pdf_bytes)
            logger.info(f"Successfully parsed IEP for student: {iep_data.student_name}")
            
            return iep_data
        except ValueError as e:
            logger.error(f"Validation error in IEP parsing: {str(e)}")
            raise HTTPException(status_code=422, detail=f"Invalid IEP format: {str(e)}")
        except RuntimeError as e:
            logger.error(f"Runtime error in IEP parsing: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error processing IEP: {str(e)}")
        
    except Exception as e:
        logger.error(f"Unexpected error in parse_iep endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/save", 
    summary="Save parsed IEP data",
    description="Save the previously parsed IEP data to create a student record with associated data.",
    response_description="Returns the created student ID and name"
)
async def save_iep(
    iep_data: IEPData,
    credentials: HTTPAuthorizationCredentials = Security(security),
    context=Depends(user_supabase_client)
):
    """
    Save the parsed IEP data to create student record with associated data.
    """
    try:
        logger.info(f"Saving IEP data for student: {iep_data.student_name}")
        
        # Get Supabase client and user ID
        supabase = context["supabase"]
        user_id = context["user_id"]
        
        # Convert grade level to integer and ensure it's within valid range (1-12)
        grade_level = 1  # Default to grade 1 if no valid grade level is found
        if iep_data.grade_level:
            # Try to extract a number from the grade level
            import re
            grade_match = re.search(r'\d+', iep_data.grade_level)
            if grade_match:
                grade_level = int(grade_match.group())
                # Ensure grade level is within valid range (1-12)
                grade_level = max(1, min(12, grade_level))
        
        # Create student record
        student_data = {
            "teacher_id": user_id,
            "name": iep_data.student_name,
            "grade_level": grade_level,
            "disability_type": iep_data.disability_type
        }
        
        student_response = supabase.table("students").insert(student_data).execute()
        if not student_response.data:
            logger.error("Failed to create student record")
            raise HTTPException(status_code=500, detail="Failed to create student record")
        
        student_id = student_response.data[0]["id"]
        logger.info(f"Created student record with ID: {student_id}")
        
        # Create subject areas, goals, and objectives
        for area in iep_data.areas_of_need:
            # Create subject area
            subject_area_data = {
                "name": area.area_name,
                "teacher_id": user_id
            }
            subject_area_response = supabase.table("subject_areas").insert(subject_area_data).execute()
            if not subject_area_response.data:
                logger.warning(f"Failed to create subject area: {area.area_name}")
                continue
            
            subject_area_id = subject_area_response.data[0]["id"]
            
            # Create goals for this subject area
            for goal in area.goals:
                goal_data = {
                    "subject_area_id": subject_area_id,
                    "teacher_id": user_id,
                    "student_id": student_id,
                    "title": goal.goal_description
                }
                goal_response = supabase.table("goals").insert(goal_data).execute()
                if not goal_response.data:
                    logger.warning(f"Failed to create goal for subject area {area.area_name}")
                    continue
                
                goal_id = goal_response.data[0]["id"]
                
                # Create objectives for this goal
                for objective in goal.objectives:
                    objective_data = {
                        "goal_id": goal_id,
                        "student_id": student_id,
                        "teacher_id": user_id,
                        "subject_area_id": subject_area_id,
                        "description": objective.description
                    }
                    objective_response = supabase.table("objectives").insert(objective_data).execute()
                    if not objective_response.data:
                        logger.warning(f"Failed to create objective for goal {goal.goal_description}")
        
        logger.info(f"Successfully saved all IEP data for student: {iep_data.student_name}")
        return {
            "message": "IEP saved successfully",
            "student_id": student_id,
            "student_name": iep_data.student_name
        }
        
    except Exception as e:
        logger.error(f"Error in save_iep endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 