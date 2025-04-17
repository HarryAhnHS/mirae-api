from fastapi import APIRouter, Depends, Query
from datetime import datetime, timedelta, timezone
from dateutil.relativedelta import relativedelta
from app.dependencies.auth import user_supabase_client

router = APIRouter()

def get_week_range(period: str):
    today = datetime.now(timezone.utc)
    # Monday = 0, Sunday = 6
    weekday = today.weekday()
    start_of_this_week = today - timedelta(days=weekday)
    start_of_this_week = start_of_this_week.replace(hour=0, minute=0, second=0, microsecond=0)

    if period == "last":
        start = start_of_this_week - timedelta(days=7)
        end = start_of_this_week
    else:  # this week
        start = start_of_this_week
        end = start + timedelta(days=7)

    return start.isoformat(), end.isoformat()

@router.get("/weekly-summary")
def get_weekly_summary(
    week: str = Query("this", regex="^(this|last)$"),
    context=Depends(user_supabase_client)
):
    supabase = context["supabase"]
    teacher_id = context["user_id"]

    start_date, end_date = get_week_range(week)

    # 1. Get all objectives for the teacher
    objectives_res = supabase \
        .table("objectives") \
        .select("id, description, student_id, subject_area_id") \
        .eq("teacher_id", teacher_id) \
        .execute()

    objectives = objectives_res.data
    objective_ids = [obj["id"] for obj in objectives]

    # 2. Get sessions logged in the given week
    sessions_res = supabase \
        .table("sessions") \
        .select("objective_id") \
        .in_("objective_id", objective_ids) \
        .gte("created_at", start_date) \
        .lt("created_at", end_date) \
        .execute()

    logged_ids = set(session["objective_id"] for session in sessions_res.data)

    # 3. Fetch students and subject areas
    student_ids = list({obj["student_id"] for obj in objectives})
    subject_ids = list({obj["subject_area_id"] for obj in objectives})

    students = {
        s["id"]: s for s in supabase.table("students")
        .select("id, name")
        .in_("id", student_ids)
        .execute().data
    }

    subjects = {
        s["id"]: s for s in supabase.table("subject_areas")
        .select("id, name")
        .in_("id", subject_ids)
        .execute().data
    }

    # 4. Build objective summary
    summary = []
    for obj in objectives:
        summary.append({
            "objective_id": obj["id"],
            "description": obj["description"],
            "student_name": students[obj["student_id"]]["name"],
            "subject_area": subjects[obj["subject_area_id"]]["name"],
            "logged_this_week": obj["id"] in logged_ids
        })

    # 5. Final summary stats
    total = len(objectives)
    logged = len(logged_ids)
    percent = round((logged / total) * 100) if total else 0

    return {
        "week": week,
        "start_date": start_date,
        "end_date": end_date,
        "progress_percent": percent,
        "objectives_logged": logged,
        "objectives_total": total,
        "objectives_left": total - logged,
        "objectives": summary
    }