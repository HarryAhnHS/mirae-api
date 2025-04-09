# mirae-api

uvicorn app.main:app --reload

# TODO 04/09/25

0. CRUD Edit and delete students, objectives, sessions.
1. Implement goals under each subject_area. goals should have title, description. 
    - Each goal has objectives.
2. objective_measure_type
- Each session is logged once a week - 1 data entry per week
- Each session needs a measure_type:
    1. trial based objectives (x/n)
    2. duration based objectives (sec/min/hours)
    3. rating scale (performance 1 - 5)
    4. binary y/n - trial out of 1
    5. frequency

3. objective progress tracking 
- objective_completion (bool), objective_completed_at
- objective_completion_percentage, objective_completion_timeline
    - Each session needs a progress goal (8 out of 10 times) at what timeline to be marked as complete.
        - Progress goal over what timeline (ex. 90% of the time in one quarter)
