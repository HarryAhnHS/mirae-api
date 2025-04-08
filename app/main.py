from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import students, objectives, sessions
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_URL")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(students.router, prefix="/students")
app.include_router(objectives.router, prefix="/objectives")
app.include_router(sessions.router, prefix="/sessions")