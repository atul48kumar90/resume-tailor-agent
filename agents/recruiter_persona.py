# agents/recruiter_persona.py

PERSONA_RULES = {
    "startup": [
        "ownership",
        "speed",
        "end-to-end delivery",
        "impact"
    ],
    "enterprise": [
        "scalability",
        "reliability",
        "cross-team collaboration",
        "process"
    ],
    "fintech": [
        "security",
        "compliance",
        "data correctness",
        "risk awareness"
    ],
    "general": []
}


def tune(resume_json: dict, persona: str) -> dict:
    resume_json["persona_emphasis"] = PERSONA_RULES.get(
        persona,
        PERSONA_RULES["general"]
    )
    return resume_json
