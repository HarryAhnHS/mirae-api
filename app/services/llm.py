import json
import os

from typing import Dict, Any
from google import genai

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL_NAME = "gemini-2.0-flash"

# Configure Gemini client
client = genai.Client(api_key=GEMINI_API_KEY)


async def analyze_session(prompt: str) -> Dict[str, Any]:
    try:
        # Call Gemini with user prompt
        response = client.models.generate_content(model=GEMINI_MODEL_NAME, contents=prompt)

        # Extract and clean response text
        content = response.text.strip()
        if content.startswith("```json"):
            content = content.split("```json")[-1].split("```")[0].strip()

        # Parse content as a list of JSON objects
        parsed = json.loads(content)

        # Validate the structure
        if not isinstance(parsed, list):
            raise ValueError("Expected a list of objective analysis results")

        cleaned = []
        for item in parsed:
            if (
                isinstance(item, dict)
                and "objective_id" in item
                and "summary" in item
                and "progress_delta" in item
            ):
                cleaned.append({
                    "objective_id": str(item["objective_id"]),
                    "summary": str(item["summary"]),
                    "progress_delta": max(-100, min(100, int(item["progress_delta"])))
                })
            else:
                raise ValueError("One or more items in the response are missing required fields")

        return {"results": cleaned}

    except json.JSONDecodeError:
        raise ValueError("Gemini response was not valid JSON")
    except Exception as e:
        print("Gemini summarization error:", e)
        return {"results": []}
