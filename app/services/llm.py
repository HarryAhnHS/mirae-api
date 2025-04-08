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

        # Extract content
        content = response.text.strip()

        # Clean up fenced code blocks if any
        if content.startswith("```json"):
            content = content.split("```json")[-1].split("```")[0].strip()

        # Parse as JSON
        parsed = json.loads(content)

        if "summary" not in parsed or "progressDelta" not in parsed:
            raise ValueError("Missing keys in Gemini output")

        parsed["progressDelta"] = max(-100, min(100, int(parsed["progressDelta"])))
        return parsed

    except json.JSONDecodeError:
        raise ValueError("Gemini response was not valid JSON")
    except Exception as e:
        print("Gemini summarization error:", e)
        return {
            "summary": "Summary unavailable due to formatting error.",
            "progressDelta": 0
        }
