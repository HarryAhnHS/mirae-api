from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Security, Body
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.dependencies.auth import user_supabase_client
from app.services.iep_parser import IEPParser
from app.schemas.student import StudentCreate
from typing import Dict, List, Optional
from pydantic import BaseModel
import uuid

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
        # Read the PDF file
        pdf_bytes = await file.read()
        
        # Parse the IEP
        parser = IEPParser()
        iep_data = await parser.parse_iep_from_pdf(pdf_bytes)
        
        return iep_data
        
    except Exception as e:
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
            raise HTTPException(status_code=500, detail="Failed to create student record")
        
        student_id = student_response.data[0]["id"]
        
        # Create subject areas, goals, and objectives
        for area in iep_data.areas_of_need:
            # Create subject area
            subject_area_data = {
                "name": area.area_name,
                "teacher_id": user_id
            }
            subject_area_response = supabase.table("subject_areas").insert(subject_area_data).execute()
            if not subject_area_response.data:
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
                    supabase.table("objectives").insert(objective_data).execute()
        
        return {
            "message": "IEP saved successfully",
            "student_id": student_id,
            "student_name": iep_data.student_name
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 