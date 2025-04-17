import os
from dotenv import load_dotenv

# Make sure to load environment variables
load_dotenv()

print("Environment Variables:")
print(f"OPENAI_GPT_MODEL: {os.getenv('OPENAI_GPT_MODEL')}")
print(f"OPENAI_API_KEY: {os.getenv('OPENAI_API_KEY')[:10]}...") # Just print the first 10 chars for safety 