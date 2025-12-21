# api/routes.py
from fastapi import (
    APIRouter,
    UploadFile,
    File,
    Form,
    BackgroundTasks,
    HTTPException,
)

from api.files import extract_text
from api.jobs import (
    create_job,
    get_job,
    update_job,
    fail_job,
)
import logging
from core.logging import request_id_ctx


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
        from agents.jd_analyzer import analyze_jd
        from agents.resume_rewriter import rewrite
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
# Primary Endpoint (JD text + resume text/file)
# ------------------------

@router.post("/tailor")
def tailor(
    background_tasks: BackgroundTasks,

    # JD inputs (exactly one required)
    job_description_text: str | None = Form(None),
    job_description_file: UploadFile | None = File(None),

    # Resume input (file only, required)
    resume_file: UploadFile = File(...),

    recruiter_persona: str = Form("general"),
):
    # ------------------------
    # Validate JD input
    # ------------------------
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

    # ------------------------
    # Extract JD text
    # ------------------------
    if job_description_file:
        try:
            jd_text = extract_text(job_description_file)
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"JD file processing failed: {str(e)}",
            )
    else:
        jd_text = job_description_text

    # ------------------------
    # Extract Resume text (file only)
    # ------------------------
    try:
        resume_text = extract_text(resume_file)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Resume file processing failed: {str(e)}",
        )

    # ------------------------
    # Create async job
    # ------------------------
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
    try:
        jd_text = extract_text(job_description)
        resume_text = extract_text(resume)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"File processing failed: {str(e)}",
        )

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
