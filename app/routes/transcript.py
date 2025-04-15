from fastapi import APIRouter, Depends, HTTPException
from app.dependencies.auth import user_supabase_client
from app.services.transcript_parser import (
    TranscriptRequest,
    ObjectiveProgress,
    ParsedSession,
    SuggestedSession,
    SuggestedSessions,
    MatchStudent,
    MatchObjective,
    call_llm_extract_sessions,
    infer_trials_completed
)
from app.utils.semantic_matcher import top_k_semantic_matches

router = APIRouter()

@router.post("/analyze", response_model=SuggestedSessions)
async def analyze_transcript_for_sessions(
    payload: TranscriptRequest,
    context=Depends(user_supabase_client)
):
    supabase = context["supabase"]
    teacher_id = context["user_id"]
    transcript = payload.transcript

    print("transcript: ", transcript)

    try:
        # parses transcript into sessions -> but LLM generated objective_titles, student_names, etc.
        parsed_sessions = call_llm_extract_sessions(transcript)
        if not parsed_sessions:
            raise HTTPException(
                status_code=422,
                detail="No valid session data found in transcript. Try rephrasing or using manual form."
            )

        # Pre-fetch all students for teacher
        students_res = (
            supabase.table("students")
            .select("id, name")
            .eq("teacher_id", teacher_id)
            .execute()
        )
        if not students_res.data:
            raise ValueError("No students found for teacher")
        students_res = students_res.data

        # Lists of valid and invalid sessions 
        session_suggestions = []

        # For each parsed session, match objective by title and teacher
        for item in parsed_sessions:
            print("For item: ", item)
            try:
                parsed = ParsedSession(**item)
            except Exception as e:
                print("❌ Failed to parse session:", item)
                print("Reason:", e)
                continue  # Could log invalid format if needed

            print("parsed: ", parsed)

            # 1. Match students semantically
            student_matches = top_k_semantic_matches(parsed.student_name, students_res, key="name", top_k=3)
            print("student_matches: ", student_matches)

            # 2. Fetch only objectives tied to matched students
            student_ids = [s["id"] for s in student_matches]
            objective_candidates = []
            for student_id in student_ids:
                obj_res = (
                    supabase.table("objectives")
                    .select("id, description, objective_type, target_accuracy")
                    .eq("teacher_id", teacher_id)
                    .eq("student_id", student_id)
                    .execute()
                )
                if obj_res.data:
                    objective_candidates.extend(obj_res.data)

            # 3. Match objective descriptions
            objective_matches = top_k_semantic_matches(
                parsed.objective_description, objective_candidates, key="description", top_k=3
            )

            # 4. Choose top match (optional: fallback if len > 1)
            top_objective = objective_matches[0] if objective_matches else None
            full_objective_meta = next(
                (obj for obj in objective_candidates if obj["id"] == top_objective["id"]), None
            ) if top_objective else None

            # 5. Re-infer trials from transcript + objective context
            if full_objective_meta:
                inferred = infer_trials_completed(
                    transcript=transcript,
                    objective_type=full_objective_meta.get("objective_type", "trial"),
                    target_accuracy=float(full_objective_meta.get("target_accuracy") or 1.0)
                )

                objective_progress = ObjectiveProgress(
                    trials_completed=inferred["trials_completed"],
                    trials_total=inferred["trials_total"]
                )
            else:
                objective_progress = ObjectiveProgress(trials_completed=0, trials_total=0)

            # 6. Build final session suggestion
            session_suggestions.append(
                SuggestedSession(
                    raw_input=transcript,
                    memo=parsed.memo,
                    objective_progress=objective_progress,
                    student_suggestions=[
                        MatchStudent(id=s["id"], name=s["name"], similarity=s["similarity"])
                        for s in student_matches
                    ],
                    objective_suggestions=[
                        MatchObjective(
                            id=o["id"], description=o["description"], similarity=o["similarity"]
                        )
                        for o in objective_matches
                    ]
                )
            )

        return SuggestedSessions(sessions=session_suggestions)

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Transcript analysis failed: {str(e)}")