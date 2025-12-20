# agents/recruiter_persona.py

from typing import Dict


def tune(resume_json: Dict, persona: str) -> Dict:
    """
    Adjust resume tone based on recruiter persona.
    For now, this is a pass-through with minor tagging.
    """

    resume_json["persona"] = persona
    return resume_json
