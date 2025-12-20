from pydantic import BaseModel
from typing import List, Optional


class TextTailorRequest(BaseModel):
    resume_text: str
    job_description: str
    recruiter_persona: Optional[str] = "general"


class TailoredResumeResponse(BaseModel):
    summary: str
    experience: List[str]
    skills: List[str]
    ats_match_percent: int
    missing_keywords: List[str]
