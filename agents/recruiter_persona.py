# agents/recruiter_persona.py
def tune(resume_json: dict, persona: str) -> dict:
    resume_json["persona"] = persona
    return resume_json
