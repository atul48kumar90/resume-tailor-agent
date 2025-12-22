from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any


class TextTailorRequest(BaseModel):
    resume_text: str = Field(..., min_length=10, description="Resume text content")
    job_description: str = Field(..., min_length=10, description="Job description text")
    recruiter_persona: Optional[str] = Field(default="general", description="Recruiter persona type")

    @validator("resume_text", "job_description")
    def validate_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("Text cannot be empty or whitespace only")
        return v.strip()


class TailoredResumeResponse(BaseModel):
    summary: str
    experience: List[str]
    skills: List[str]
    ats_match_percent: int
    missing_keywords: List[str]


class RewrittenResumeRequest(BaseModel):
    """Request body for /ats/download endpoint"""
    summary: Optional[str] = Field(default="", description="Resume summary")
    experience: List[Dict[str, Any]] = Field(default_factory=list, description="Experience entries")
    skills: List[str] = Field(default_factory=list, description="List of skills")

    @validator("experience")
    def validate_experience(cls, v):
        for exp in v:
            if not isinstance(exp, dict):
                raise ValueError("Experience entries must be dictionaries")
            if "title" not in exp:
                raise ValueError("Experience entry must have 'title' field")
            if "bullets" not in exp:
                raise ValueError("Experience entry must have 'bullets' field")
        return v


class ChatIntentRequest(BaseModel):
    """Request body for chat edit endpoints"""
    action: str = Field(..., description="Action type: add_skill, remove_skill, rewrite_bullet, rewrite_summary")
    skill: Optional[str] = Field(None, description="Skill name (for add_skill/remove_skill)")
    index: Optional[int] = Field(None, description="Bullet index (for rewrite_bullet)")
    exp_index: Optional[int] = Field(None, description="Experience index (for rewrite_bullet)")
    summary: Optional[str] = Field(None, description="Change summary")
    requires_approval: Optional[bool] = Field(default=False)
    risk_level: Optional[str] = Field(default="low")

    @validator("action")
    def validate_action(cls, v):
        allowed = ["add_skill", "remove_skill", "rewrite_bullet", "rewrite_summary"]
        if v not in allowed:
            raise ValueError(f"Action must be one of: {', '.join(allowed)}")
        return v


class RoleInfoRequest(BaseModel):
    """Request body for template recommendation"""
    role: str = Field(..., description="Detected role")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    signals: Optional[Dict[str, int]] = Field(default_factory=dict)


class BatchJDRequest(BaseModel):
    """Request body for batch processing"""
    jd_id: str = Field(..., description="Unique identifier for this JD")
    jd_text: str = Field(..., min_length=10, description="Job description text")
    title: Optional[str] = Field(None, description="Job title (optional)")


class BatchProcessRequest(BaseModel):
    """Request for batch processing multiple JDs"""
    resume_text: Optional[str] = Field(None, description="Resume text (if not uploading file)")
    jds: List[BatchJDRequest] = Field(..., min_items=1, max_items=20, description="List of job descriptions")
    resume_id: Optional[str] = Field(None, description="Resume ID for tracking")
