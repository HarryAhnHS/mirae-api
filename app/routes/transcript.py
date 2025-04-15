from fastapi import APIRouter, Depends, HTTPException, Body
from uuid import uuid4
from app.dependencies.auth import user_supabase_client
from typing import List
from app.services.transcript_parser import (
    TranscriptRequest,
    ObjectiveProgress,
    ParsedSession,
    SuggestedSession,
    MatchStudent,
    MatchObjective,
    call_llm_extract_sessions,
    infer_trials_completed
)
from app.utils.semantic_matcher import top_k_semantic_matches

router = APIRouter()

@router.post("/analyze", response_model=List[SuggestedSession])
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
            .select("id, name, grade_level, disability_type")
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
            try:
                parsed = ParsedSession(**item)
            except Exception as e:
                print("❌ Failed to parse session:", item)
                print("Reason:", e)
                continue  # Could log invalid format if needed

            # 1. Match students semantically
            student_matches = top_k_semantic_matches(parsed.student_name, students_res, key="name", top_k=3)
            print("student_matches: ", student_matches)

            # 2. Fetch only objectives tied to matched students
            student_ids = [s["id"] for s in student_matches]
            objective_candidates = []
            for student_id in student_ids:
                obj_res = (
                    supabase.table("objectives")
                    .select("""
                        id, description, objective_type, target_accuracy, student:students(*)
                    """)
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
                    objective_description=top_objective["description"],
                    objective_student_name=full_objective_meta["student"]["name"],
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
                            id=o["id"], description=o["description"], similarity=o["similarity"], queried_objective_description=parsed.objective_description
                        )
                        for o in objective_matches
                    ]
                )
            )

        return session_suggestions

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Transcript analysis failed: {str(e)}")
    
@router.post("/format")
async def format_analysis(
    sessions: List[SuggestedSession] = Body(...),
    context=Depends(user_supabase_client)   
):
    supabase = context["supabase"]

    try:
        # Gather all unique IDs across responses
        objective_ids = set()
        student_ids = set()

        for session in sessions:
            for obj in session.objective_suggestions:
                objective_ids.add(obj.id)
            for student in session.student_suggestions:
                student_ids.add(student.id)

        # Fetch all relevant objective metadata
        objective_lookup = {}
        if objective_ids:
            objs_res = supabase.table("objectives").select("""
                id, description, objective_type, target_accuracy, student_id,
                goal:goals(id, title),
                subject_area:subject_areas(id, name)
            """).in_("id", list(objective_ids)).execute()
            for obj in objs_res.data:
                objective_lookup[obj["id"]] = obj

        # Fetch all student metadata
        student_lookup = {}
        if student_ids:
            students_res = supabase.table("students").select("*").in_("id", list(student_ids)).execute()
            for stu in students_res.data:
                student_lookup[stu["id"]] = stu

        # Final output format
        formatted = []

        for session in sessions:
            student_list = [
                student_lookup.get(student.id) for student in session.student_suggestions
            ]

            objective_list = []
            for obj_suggestion in session.objective_suggestions:
                obj_id = obj_suggestion.id
                objective = objective_lookup.get(obj_id)
                if not objective:
                    continue

                subject_area = objective.get("subject_area")
                goal = objective.get("goal")

                objective_list.append({
                    "id": objective["id"],
                    "description": objective["description"],
                    "objective_type": objective["objective_type"],
                    "target_accuracy": objective["target_accuracy"],
                    "similarity": obj_suggestion.similarity,
                    "queried_objective_description": obj_suggestion.queried_objective_description,
                    "subject_area": {
                        "id": subject_area["id"],
                        "name": subject_area["name"]
                    } if subject_area else None,
                    "goal": {
                        "id": goal["id"],
                        "title": goal["title"]
                    } if goal else None
                })

            # Final response format for each 
            formatted.append({
                "parsed_session_id": str(uuid4()),
                "students": student_list,
                "objectives": objective_list,
                "memo": session.memo,
                "objective_progress": session.objective_progress,
                "raw_input": session.raw_input
            })

        return formatted

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to format analysis: {str(e)}")
    
# Sample prompt: John and Bobby both took the exact same math test today, and John got 15 out of 20 right. But bobby only got 50% right. John struggled with long division.
# Sample formatted response:
# [
#     {
#         "parsed_session_id": "fc5cf586-3f88-4e29-82f1-4646ca1328bd",
#         "students": [
#             {
#                 "id": "a838dc9c-c7db-4f33-ac04-0aa90659d551",
#                 "name": "John",
#                 "grade_level": 10,
#                 "disability_type": "adas",
#                 "created_at": "2025-04-08T08:03:20.386766+00:00",
#                 "updated_at": "2025-04-08T08:03:20.386766+00:00",
#                 "teacher_id": "40ebd547-a141-4a0a-b61b-369564bca6bb",
#                 "summary": null
#             },
#             {
#                 "id": "2e678888-5c54-4e5a-a843-a19e166b6932",
#                 "name": "Bobby",
#                 "grade_level": 12,
#                 "disability_type": "",
#                 "created_at": "2025-04-13T07:05:01.055007+00:00",
#                 "updated_at": "2025-04-13T07:05:01.055007+00:00",
#                 "teacher_id": "40ebd547-a141-4a0a-b61b-369564bca6bb",
#                 "summary": null
#             },
#             {
#                 "id": "1b7faeb3-b3b3-4ee8-a7bd-6899c27d9333",
#                 "name": "Julian Danna",
#                 "grade_level": 10,
#                 "disability_type": "Other Health Impaired",
#                 "created_at": "2025-04-14T05:24:44.97185+00:00",
#                 "updated_at": "2025-04-14T05:24:44.97185+00:00",
#                 "teacher_id": "40ebd547-a141-4a0a-b61b-369564bca6bb",
#                 "summary": null
#             }
#         ],
#         "objectives": [
#             {
#                 "id": "59389ed9-0692-4c15-9425-34be4c3f4544",
#                 "description": "Get 80% or more on his math assessment.",
#                 "objective_type": "trial",
#                 "target_accuracy": 0.8,
#                 "similarity": 0.5927335023880005,
#                 "queried_objective_description": "John is working on taking a math test.",
#                 "subject_area": {
#                     "id": "66833d1e-af00-4343-8e23-0a26f3ae5020",
#                     "name": "Subject 5"
#                 },
#                 "goal": {
#                     "id": "77105fd8-1971-4a5b-875a-dcd83c52a78e",
#                     "title": "Goal 5 for subject 5"
#                 }
#             },
#             {
#                 "id": "59b7ea2f-33d0-430c-b120-8fa66b1fb07e",
#                 "description": "Bobby should get 80% or higher on a simple arithmetic math exam, over 4 out of 5 trials. ",
#                 "objective_type": "trial",
#                 "target_accuracy": 0.8,
#                 "similarity": 0.46193811297416687,
#                 "queried_objective_description": "John is working on taking a math test.",
#                 "subject_area": {
#                     "id": "40e274a1-7bca-456f-bd13-a7a38f0cfcc6",
#                     "name": "Academic"
#                 },
#                 "goal": {
#                     "id": "2698a8fc-a7be-4dd7-abff-aa466f8a105b",
#                     "title": "Mathematics and Computation"
#                 }
#             },
#             {
#                 "id": "3378a707-4044-4c8e-a5c3-4a8de56df87e",
#                 "description": "John will pronounce his R's correctly with more than 80% accuracy across 4/5 entries.",
#                 "objective_type": "trial",
#                 "target_accuracy": 0.8,
#                 "similarity": 0.427319198846817,
#                 "queried_objective_description": "John is working on taking a math test.",
#                 "subject_area": {
#                     "id": "fe9f71cf-2dbf-4d2d-a3e2-6eef221995ec",
#                     "name": "Speech / Language"
#                 },
#                 "goal": {
#                     "id": "013b2610-34db-4b41-a31a-682276485ecd",
#                     "title": "Improve Speaking and Pronounciation"
#                 }
#             }
#         ],
#         "memo": "John scored 15 out of 20, struggling with long division.",
#         "objective_progress": {
#             "trials_completed": 15,
#             "trials_total": 20
#         },
#         "raw_input": "John and Bobby both took the exact same math test today, and John got 15 out of 20 right. But bobby only got 50% right. John struggled with long division."
#     },
#     {
#         "parsed_session_id": "9d316de1-0b15-4595-98be-f9b6e156df12",
#         "students": [
#             {
#                 "id": "2e678888-5c54-4e5a-a843-a19e166b6932",
#                 "name": "Bobby",
#                 "grade_level": 12,
#                 "disability_type": "",
#                 "created_at": "2025-04-13T07:05:01.055007+00:00",
#                 "updated_at": "2025-04-13T07:05:01.055007+00:00",
#                 "teacher_id": "40ebd547-a141-4a0a-b61b-369564bca6bb",
#                 "summary": null
#             },
#             {
#                 "id": "a838dc9c-c7db-4f33-ac04-0aa90659d551",
#                 "name": "John",
#                 "grade_level": 10,
#                 "disability_type": "adas",
#                 "created_at": "2025-04-08T08:03:20.386766+00:00",
#                 "updated_at": "2025-04-08T08:03:20.386766+00:00",
#                 "teacher_id": "40ebd547-a141-4a0a-b61b-369564bca6bb",
#                 "summary": null
#             },
#             {
#                 "id": "d61cb8f0-d9b3-4e4b-9e29-629a9a9dea1d",
#                 "name": "Jayden Latimer",
#                 "grade_level": 1,
#                 "disability_type": "Communication Impairment (CI)",
#                 "created_at": "2025-04-14T06:36:01.64613+00:00",
#                 "updated_at": "2025-04-14T06:36:01.64613+00:00",
#                 "teacher_id": "40ebd547-a141-4a0a-b61b-369564bca6bb",
#                 "summary": null
#             }
#         ],
#         "objectives": [
#             {
#                 "id": "59b7ea2f-33d0-430c-b120-8fa66b1fb07e",
#                 "description": "Bobby should get 80% or higher on a simple arithmetic math exam, over 4 out of 5 trials. ",
#                 "objective_type": "trial",
#                 "target_accuracy": 0.8,
#                 "similarity": 0.7604694962501526,
#                 "queried_objective_description": "Bobby is working on taking a math test.",
#                 "subject_area": {
#                     "id": "40e274a1-7bca-456f-bd13-a7a38f0cfcc6",
#                     "name": "Academic"
#                 },
#                 "goal": {
#                     "id": "2698a8fc-a7be-4dd7-abff-aa466f8a105b",
#                     "title": "Mathematics and Computation"
#                 }
#             },
#             {
#                 "id": "59389ed9-0692-4c15-9425-34be4c3f4544",
#                 "description": "Get 80% or more on his math assessment.",
#                 "objective_type": "trial",
#                 "target_accuracy": 0.8,
#                 "similarity": 0.5445058345794678,
#                 "queried_objective_description": "Bobby is working on taking a math test.",
#                 "subject_area": {
#                     "id": "66833d1e-af00-4343-8e23-0a26f3ae5020",
#                     "name": "Subject 5"
#                 },
#                 "goal": {
#                     "id": "77105fd8-1971-4a5b-875a-dcd83c52a78e",
#                     "title": "Goal 5 for subject 5"
#                 }
#             },
#             {
#                 "id": "e9726fca-16d9-4bfa-a921-6ea5c87d6486",
#                 "description": "Given when asked by the teacher, Jayden will identify numbers up to 10 by naming, on 4 out of 5 trials, as evaluated/determined by Formal/Informal Assessments At Opportunity, by 04/26/2024.",
#                 "objective_type": "trial",
#                 "target_accuracy": null,
#                 "similarity": 0.35215622186660767,
#                 "queried_objective_description": "Bobby is working on taking a math test.",
#                 "subject_area": {
#                     "id": "043b0c56-b7ae-477d-a72e-3506554b1272",
#                     "name": "Mathematics"
#                 },
#                 "goal": {
#                     "id": "37679c4a-958b-4d6f-8b87-89eff55b9589",
#                     "title": "Given specialized instruction with growth and improvement in math skills, Jayden will understand counting and cardinality, at 80% mastery, as evaluated/determined by Data Collection Quarterly, by 04/26/2024."
#                 }
#             }
#         ],
#         "memo": "Bobby scored 50% right.",
#         "objective_progress": {
#             "trials_completed": 10,
#             "trials_total": 20
#         },
#         "raw_input": "John and Bobby both took the exact same math test today, and John got 15 out of 20 right. But bobby only got 50% right. John struggled with long division."
#     }
# ]