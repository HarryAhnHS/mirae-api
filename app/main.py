from fastapi import FastAPI
from app.routes import auth, students, objectives, sessions

app = FastAPI()

# app.include_router(auth.router, prefix="/auth")
# app.include_router(students.router, prefix="/students")
# app.include_router(objectives.router, prefix="/objectives")
app.include_router(sessions.router, prefix="/sessions")