from fastapi import APIRouter, UploadFile, File, HTTPException
from api.schemas import TextTailorRequest, TailoredResumeResponse
from api.dependencies import read_file

from agents.jd_analyzer import analyze_jd
from agents.resume_rewriter import rewrite
from agents.ats_scorer import score
from agents.recruiter_persona import tune

router = APIRouter()


# ---------------------------
# Health Check
# ---------------------------
@router.get("/health")
def health():
    return {"status": "healthy"}


# ---------------------------
# Tailor Resume (TEXT)
# ---------------------------
@router.post("/tailor/text", response_model=TailoredResumeResponse)
def tailor_from_text(request: TextTailorRequest):

    jd_data = analyze_jd(request.job_description)

    rewritten = rewrite(
        jd=request.job_description,
        resume=request.resume_text
    )

    ats = score(
        jd_data["ats_keywords"],
        request.resume_text
    )

    final_resume = tune(
        rewritten,
        request.recruiter_persona
    )

    return {
        "summary": final_resume["summary"],
        "experience": final_resume["experience"],
        "skills": final_resume["skills"],
        "ats_match_percent": ats["match_percent"],
        "missing_keywords": ats["missing_keywords"]
    }


# ---------------------------
# Tailor Resume (FILES)
# ---------------------------
@router.post("/tailor/files", response_model=TailoredResumeResponse)
async def tailor_from_files(
    resume_file: UploadFile = File(...),
    jd_file: UploadFile = File(...),
    recruiter_persona: str = "general"
):

    resume_text = await read_file(resume_file)
    jd_text = await read_file(jd_file)

    jd_data = analyze_jd(jd_text)

    rewritten = rewrite(jd=jd_text, resume=resume_text)

    ats = score(jd_data["ats_keywords"], resume_text)

    final_resume = tune(rewritten, recruiter_persona)

    return {
        "summary": final_resume["summary"],
        "experience": final_resume["experience"],
        "skills": final_resume["skills"],
        "ats_match_percent": ats["match_percent"],
        "missing_keywords": ats["missing_keywords"]
    }
