import re
from typing import Optional, Dict, Any, Tuple
import logging

logger = logging.getLogger(__name__)

def extract_fraction(description: str) -> Tuple[Optional[int], Optional[int]]:
    """
    Extract trial fractions like "4/5", "3 out of 5", "on 4 out of 5 trials", etc.
    
    Args:
        description: The objective text to parse
        
    Returns:
        A tuple containing:
        - The numerator (target successes) as an integer, or None if not found
        - The denominator (total trials) as an integer, or None if not found
    """
    # Match patterns like "4/5", "4 out of 5", "on 4 out of 5 opportunities/trials"
    fraction_patterns = [
        r'(\d+)\s*(?:\/|out of|of)\s*(\d+)\s*(?:opportunities|trials|opportunities\/trials)',
        r'(\d+)\s*(?:\/|out of)\s*(\d+)',
        r'on\s+(\d+)\s*(?:\/|out of|of)\s*(\d+)'
    ]
    
    for pattern in fraction_patterns:
        match = re.search(pattern, description.lower())
        if match:
            try:
                num_int = int(match.group(1))
                denom_int = int(match.group(2))
                return num_int, denom_int
            except ValueError:
                pass
    
    return None, None

def extract_accuracy(description: str) -> Optional[float]:
    """
    Extract accuracy percentages like "80% mastery", "with 75% accuracy", etc.
    
    Args:
        description: The objective text to parse
        
    Returns:
        A float with the percentage (e.g., 80.0), or None if not found
    """
    # Match patterns like "80% mastery", "with 75% accuracy", "at 90%"
    accuracy_patterns = [
        r'(\d+)%\s*(?:mastery|accuracy|proficiency)',
        r'(?:with|at)\s+(\d+)%',
        r'(\d+)\s*%'
    ]
    
    for pattern in accuracy_patterns:
        match = re.search(pattern, description.lower())
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                return None
    
    return None

def extract_frequency(description: str) -> Optional[str]:
    """
    Extract assessment frequency like "Daily", "Weekly", "At Opportunity", etc.
    
    Args:
        description: The objective text to parse
        
    Returns:
        The frequency string, or None if not found
    """
    # Common frequency keywords in IEPs
    frequency_keywords = {
        "daily": "Daily",
        "weekly": "Weekly",
        "monthly": "Monthly", 
        "quarterly": "Quarterly",
        "at opportunity": "At Opportunity",
        "observation daily": "Observation Daily",
        "formal/informal assessments at opportunity": "Formal/Informal Assessments At Opportunity",
        "data collection quarterly": "Data Collection Quarterly",
        "as evaluated/determined by": "As Evaluated/Determined"
    }
    
    desc_lower = description.lower()
    
    # Search for each frequency keyword in the description
    for keyword, formatted_value in frequency_keywords.items():
        if keyword in desc_lower:
            return formatted_value
    
    # Check for any mention of assessment timing
    assessment_match = re.search(r'as (?:evaluated|determined|assessed)(?:/determined)? by\s+([^,\.]+)', desc_lower)
    if assessment_match:
        return assessment_match.group(1).strip().title()
    
    return None

def determine_objective_type(description: str) -> str:
    """
    Determine the type of objective based on its description.
    
    Args:
        description: The objective text to parse
        
    Returns:
        Objective type: "trials", "binary", "rubric", "continuous", or default "trials"
    """
    desc_lower = description.lower()
    
    # Binary objectives typically use yes/no, success/failure language
    binary_indicators = [
        "yes/no", "yes or no", "success/failure", "pass/fail", 
        "complete/incomplete", "completed/not completed"
    ]
    
    # Rubric objectives mention scoring guides or point scales
    rubric_indicators = [
        "rubric", "scoring guide", "scale of", "point scale", 
        "rating of", "score of at least"
    ]
    
    # Check for binary type
    if any(indicator in desc_lower for indicator in binary_indicators):
        return "binary"
    
    # Check for rubric type
    if any(indicator in desc_lower for indicator in rubric_indicators):
        return "rubric"
    
    # Check for trials keywords
    if re.search(r'(\d+)\s*(?:\/|out of|of)\s*(\d+)', desc_lower):
        return "trials"
    
    # Check for continuous measurement language
    if re.search(r'(measure|track|record|log|monitor|document)', desc_lower):
        return "continuous"
    
    # Default if nothing else matches
    return "trials"  # Most common type as default

def parse_objective(description: str) -> Dict[str, Any]:
    """
    Parse an objective description to extract database-relevant fields.
    
    Args:
        description: The objective text to parse
        
    Returns:
        Dictionary with all parsed fields, using None for missing values
    """
    logger.info(f"Parsing objective: {description[:50]}...")
    
    # Initialize with required field
    result = {
        "description": description.strip() if description else ""
    }
    
    try:
        # Try to extract data but don't fail if anything goes wrong
        target_consistency_successes, target_consistency_trials = extract_fraction(description)
        target_accuracy = extract_accuracy(description)
        reporting_frequency = extract_frequency(description)
        objective_type = determine_objective_type(description)
        
        # Add extracted data to result, using None for missing values
        result.update({
            "objective_type": objective_type,
            "target_accuracy": target_accuracy,
            "target_consistency_trials": target_consistency_trials,
            "target_consistency_successes": target_consistency_successes,
            "reporting_frequency": reporting_frequency
        })
        
        logger.debug(f"Parsed objective details: {result}")
    except Exception as e:
        # Log the error but continue with default values
        logger.warning(f"Error parsing objective details: {str(e)}")
    
    return result 