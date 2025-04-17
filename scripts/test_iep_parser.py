#!/usr/bin/env python3
"""
Test script for the enhanced IEP parser.

Usage:
    python3 scripts/test_iep_parser.py path/to/iep.pdf
"""

import sys
import os
import json
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Add the parent directory to the sys.path to import app modules
sys.path.append(str(Path(__file__).parent.parent))

from app.services.iep_parser import IEPParser
from app.services.objective_parser import parse_objective

async def test_parse_pdf(pdf_path):
    """Parse a PDF file and print the extracted data."""
    print(f"Parsing IEP from file: {pdf_path}")
    
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()
    
    parser = IEPParser()
    try:
        iep_data = await parser.parse_iep_from_pdf(pdf_bytes)
        
        # Convert to dict for pretty printing
        iep_dict = iep_data.dict()
        
        # Print summary
        print("\n=== IEP Summary ===")
        print(f"Student: {iep_dict['student_name']}")
        print(f"Disability: {iep_dict['disability_type']}")
        print(f"Grade Level: {iep_dict['grade_level']}")
        
        total_areas = len(iep_dict['areas_of_need'])
        total_goals = sum(len(area['goals']) for area in iep_dict['areas_of_need'])
        total_objectives = sum(
            sum(len(goal['objectives']) for goal in area['goals']) 
            for area in iep_dict['areas_of_need']
        )
        
        print(f"Areas of Need: {total_areas}")
        print(f"Goals: {total_goals}")
        print(f"Objectives: {total_objectives}")
        
        # Print detailed breakdown of objectives with enhanced parsing
        print("\n=== Enhanced Objective Details ===")
        for area_idx, area in enumerate(iep_dict['areas_of_need']):
            print(f"\nArea {area_idx+1}: {area['area_name']}")
            
            for goal_idx, goal in enumerate(area['goals']):
                print(f"  Goal {goal_idx+1}: {goal['goal_description'][:100]}...")
                
                for obj_idx, obj in enumerate(goal['objectives']):
                    print(f"    Objective {obj_idx+1}:")
                    print(f"      Description: {obj['description'][:80]}..." if 'description' in obj and obj['description'] else "      Description: None")
                    print(f"      Trials: {obj.get('trials_fraction', 'None')}")
                    print(f"      Target Accuracy: {obj.get('target_accuracy', 'None')}")
                    print(f"      Frequency: {obj.get('frequency', 'None')}")
                    print(f"      Target Date: {obj.get('target_date', 'None')}")
                    print(f"      Type: {obj.get('objective_type', 'None')}")
                    print(f"      Supports: {obj.get('supports', 'None')}")
                    print(f"      Target Consistency Trials: {obj.get('target_consistency_trials', 'None')}")
                    print(f"      Target Consistency Successes: {obj.get('target_consistency_successes', 'None')}")
                    print(f"      Reporting Frequency: {obj.get('reporting_frequency', 'None')}")
        
        # Save the parsed data to a JSON file
        output_file = Path(pdf_path).with_suffix('.json')
        with open(output_file, "w") as f:
            json.dump(iep_dict, f, indent=2)
        
        print(f"\nParsed data saved to: {output_file}")
        
    except Exception as e:
        print(f"Error parsing IEP: {str(e)}")
        raise

def test_objective_parser():
    """Test the objective parser with some example objectives."""
    print("\n=== Testing Objective Parser ===")
    test_objectives = [
        "Given Individual/Group opportunities, Jayden will Participate in a pretend play scheme with another child (doll play, dramatic play, cars/trucks, blocks, etc.) by Accepting or offering toys/materials from another child, on 4/5 opportunities/trials, as evaluated/determined by Observation Daily, by 06/21/2023.",
        "Given Verbal and visual prompts, Jayden will Completing calendar/weather and other early learning activities, on 4/5 opportunities/trials, as evaluated/determined by Observation Daily, by 06/21/2023.",
        "Given a list of upper and lower case letters, Jayden will identify letters through naming, on 4 out of 5 trials, as evaluated/determined by Formal/Informal Assessments At Opportunity, by 04/26/2024.",
        "Given a story at instructional level, Jayden will With prompting and support, be able to ask and answer questions about key details in a text. (e.g., who, what, where, when, why, how). , on 4 out of 5 trials, as evaluated/determined by Formal/Informal Assessments At Opportunity, by 04/26/2024.",
        "Given paper and pencil, Jayden will read, print and spell his own name, on 4 out of 5, as evaluated/determined by Formal/Informal Assessments At Opportunity, by 04/26/2024.",
        "Given when asked by the teacher, Jayden will count orally to 20, on 4 out of 5 trials, as evaluated/determined by Formal/Informal Assessments At Opportunity, by 04/26/2024.",
        "Given a short story, Jayden will answer corresponding \"WH\" questions, independently, with 80% accuracy, across 4 out of 5 data collections, as evaluated/determined by Data Collection At Opportunity, by 04/26/2024.",
        # Add a poorly formatted objective to test leniency
        "Student will improve skills."
    ]
    
    for i, obj in enumerate(test_objectives):
        print(f"\nTest Objective {i+1}:")
        print(f"Text: {obj}")
        result = parse_objective(obj)
        print("Parsed data:")
        for key, value in result.items():
            if key != "description":  # Skip printing the full description again
                print(f"  {key}: {value}")

def simulate_iep_workflow():
    """
    Simulates processing a full IEP with objectives that need additional attributes.
    This shows what would happen in the API workflows.
    """
    print("\n=== Simulating Complete IEP Workflow ===")
    
    # Create a mock IEP with multiple areas, goals, and objectives
    mock_iep = {
        "student_name": "Jayden Smith",
        "disability_type": "Specific Learning Disability",
        "grade_level": "Grade 5",
        "areas_of_need": [
            {
                "area_name": "Mathematics",
                "goals": [
                    {
                        "goal_description": "Jayden will improve math skills",
                        "objectives": [
                            {"description": "Given 20 single-digit addition problems, Jayden will solve with 80% accuracy, across 4 out of 5 trials."},
                            {"description": "Student will complete 10 subtraction problems."}
                        ]
                    }
                ]
            },
            {
                "area_name": "Reading",
                "goals": [
                    {
                        "goal_description": "Jayden will improve reading comprehension",
                        "objectives": [
                            {"description": "Given a grade-level text, Jayden will answer comprehension questions with 75% accuracy on 3/4 attempts."}
                        ]
                    }
                ]
            }
        ]
    }
    
    # Import necessary modules from the app
    from app.services.iep_parser import clean_model_output
    
    # Process the IEP as it would happen in the API
    cleaned_data = clean_model_output(mock_iep)
    
    # Print the processed IEP data
    print("\nProcessed IEP Data:")
    print(f"Student: {cleaned_data['student_name']}")
    print(f"Disability: {cleaned_data['disability_type']}")
    print(f"Grade: {cleaned_data['grade_level']}")
    
    # Print processed objectives with their extracted details
    print("\nProcessed Objectives:")
    for area_idx, area in enumerate(cleaned_data['areas_of_need']):
        print(f"\nArea {area_idx+1}: {area['area_name']}")
        
        for goal_idx, goal in enumerate(area['goals']):
            print(f"  Goal {goal_idx+1}: {goal['goal_description']}")
            
            for obj_idx, obj in enumerate(goal['objectives']):
                print(f"    Objective {obj_idx+1}: {obj['description'][:80]}...")
                # Print the extracted fields that would be saved to the database
                print(f"      objective_type: {obj.get('objective_type', 'None')}")
                print(f"      target_accuracy: {obj.get('target_accuracy', 'None')}")
                print(f"      target_consistency_trials: {obj.get('target_consistency_trials', 'None')}")
                print(f"      target_consistency_successes: {obj.get('target_consistency_successes', 'None')}")
                print(f"      reporting_frequency: {obj.get('reporting_frequency', 'None')}")

if __name__ == "__main__":
    # Load environment variables
    load_dotenv()
    
    # Test objective parser with example objectives
    test_objective_parser()
    
    # Simulate complete IEP workflow
    simulate_iep_workflow()
    
    # Test PDF parsing if a file is provided
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
        if os.path.exists(pdf_path):
            asyncio.run(test_parse_pdf(pdf_path))
        else:
            print(f"Error: File '{pdf_path}' not found.")
            sys.exit(1)
    else:
        print("\nNo PDF file provided. To test PDF parsing, provide a path to an IEP PDF:")
        print("python3 scripts/test_iep_parser.py path/to/iep.pdf") 