# api/routes.py
from fastapi import (
    APIRouter,
    UploadFile,
    File,
    Form,
    BackgroundTasks,
    HTTPException,
)

import logging

from api.files import extract_text
from api.jobs import (
    create_job,
    get_job,
    update_job,
    fail_job,
)

from agents.jd_analyzer import analyze_jd
from agents.resume_rewriter import rewrite
from agents.ats_scorer import (
    score_detailed,
    attribute_keywords_to_bullets,
)

from core.cache import get_cached_jd, set_cached_jd

router = APIRouter()


# ------------------------
# Health Check
# ------------------------

@router.get("/health")
def health():
    return {"status": "ok"}


# ------------------------
# Background Job Processor
# ------------------------

def process_resume_job(job_id: str, jd: str, resume: str, persona: str):
    logger = logging.getLogger(__name__)
    logger.info(f"Processing job {job_id}")

    try:
        from agents.ats_scorer import score
        from agents.recruiter_persona import tune

        jd_data = analyze_jd(jd)
        rewritten = rewrite(jd, resume)
        ats = score(jd_data.get("ats_keywords", []), resume)
        final = tune(rewritten, persona)

        update_job(job_id, {
            "resume": final,
            "ats": ats,
            "jd_analysis": jd_data,
        })

    except Exception as e:
        logger.exception(f"Unhandled error while processing job {job_id}")
        fail_job(job_id, str(e))


def process_resume_files_job(
    job_id: str,
    jd_text: str,
    resume_text: str,
    persona: str,
):
    process_resume_job(job_id, jd_text, resume_text, persona)


# ------------------------
# Primary Endpoint
# ------------------------

@router.post("/tailor")
def tailor(
    background_tasks: BackgroundTasks,
    job_description_text: str | None = Form(None),
    job_description_file: UploadFile | None = File(None),
    resume_file: UploadFile = File(...),
    recruiter_persona: str = Form("general"),
):
    if not job_description_text and not job_description_file:
        raise HTTPException(
            status_code=400,
            detail="Either job_description_text or job_description_file must be provided",
        )

    if job_description_text and job_description_file:
        raise HTTPException(
            status_code=400,
            detail="Provide only one of job_description_text or job_description_file",
        )

    jd_text = (
        extract_text(job_description_file)
        if job_description_file
        else job_description_text
    )

    resume_text = extract_text(resume_file)

    job_id = create_job()

    background_tasks.add_task(
        process_resume_job,
        job_id,
        jd_text,
        resume_text,
        recruiter_persona,
    )

    return {
        "job_id": job_id,
        "status": "processing",
    }


# ------------------------
# File-Only Convenience Endpoint
# ------------------------

@router.post("/tailor/files")
def tailor_files(
    background_tasks: BackgroundTasks,
    job_description: UploadFile = File(...),
    resume: UploadFile = File(...),
    recruiter_persona: str = Form("general"),
):
    jd_text = extract_text(job_description)
    resume_text = extract_text(resume)

    job_id = create_job()

    background_tasks.add_task(
        process_resume_files_job,
        job_id,
        jd_text,
        resume_text,
        recruiter_persona,
    )

    return {
        "job_id": job_id,
        "status": "processing",
    }


# ------------------------
# Job Status Endpoint
# ------------------------

@router.get("/jobs/{job_id}")
def job_status(job_id: str):
    job = get_job(job_id)

    if not job:
        raise HTTPException(
            status_code=404,
            detail="Job not found",
        )

    return job


# ------------------------
# ATS Compare Endpoint
# ------------------------

@router.post("/ats/compare")
def compare_ats(
    job_description: str = Form(None),
    jd_file: UploadFile | None = File(None),
    resume: UploadFile = File(...),
):
    if not job_description and not jd_file:
        raise HTTPException(400, "JD text or file required")

    jd_text = extract_text(jd_file) if jd_file else job_description
    resume_text = extract_text(resume)

    # ---- JD analysis with Redis cache ----
    jd_data = get_cached_jd(jd_text)
    if not jd_data:
        jd_data = analyze_jd(jd_text)
        set_cached_jd(jd_text, jd_data)

    jd_keywords = {
        "required_skills": jd_data["required_skills"],
        "optional_skills": jd_data["optional_skills"],
        "tools": jd_data["tools"],
    }

    before = score_detailed(jd_keywords, resume_text)

    # ---- Rewrite resume ----
    rewritten = rewrite(jd_text, resume_text)

    rewritten_text = (
        rewritten.get("summary", "")
        + "\n"
        + "\n".join(
            bullet
            for exp in rewritten.get("experience", [])
            for bullet in exp.get("bullets", [])
        )
    )

    after = score_detailed(jd_keywords, rewritten_text)

    # 5️⃣ Keyword attribution (AFTER only – makes sense)
    attribution = attribute_keywords_to_bullets(
        jd_keywords,
        rewritten.get("experience", []),
    )


    # ---- Risk calculation ----
    def ats_risk(score: int) -> str:
        if score < 50:
            return "high"
        if score < 70:
            return "medium"
        return "low"

    risk = {
        "before": ats_risk(before["score"]),
        "after": ats_risk(after["score"]),
    }

    # ---- Improvement ----
    improvement = {
        "score_delta": after["score"] - before["score"],
        "newly_added_keywords": list(
            set(after["matched_keywords"]) - set(before["matched_keywords"])
        ),
    }

    return {
        "before": before,
        "after": after,
        "improvement": improvement,
        "risk": risk,
        "keyword_attribution": attribution,
    }
