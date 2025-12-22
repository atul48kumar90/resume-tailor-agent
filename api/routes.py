# api/routes.py
from fastapi import (
    APIRouter,
    UploadFile,
    File,
    Form,
    BackgroundTasks,
    HTTPException,
)
from typing import List

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
from agents.keyword_confidence import keyword_confidence
from agents.resume_risk import resume_risk_flags
from agents.jd_fit import classify_jd_fit
from agents.skill_inference import infer_skills_from_resume
from agents.role_confidence import tune_confidence_by_role
from agents.role_detector import detect_role
from agents.role_rules import ROLE_CONFIDENCE_THRESHOLDS
from agents.jd_normalizer import normalize_jd_keywords
from fastapi.responses import StreamingResponse, FileResponse
from agents.resume_formatter import format_resume_text, format_resume_sections
from agents.templates.registry import TEMPLATES
from agents.templates.pdf_renderer import render_pdf
from agents.templates.recommender import recommend_templates
from agents.exporters.txt_exporter import export_txt
from agents.exporters.zip_exporter import export_zip
from agents.resume_versions import get_current_version
import tempfile




router = APIRouter()


# ------------------------
# Health Check
# ------------------------

@router.get("/health")
def health():
    """
    Comprehensive health check endpoint.
    Checks Redis connectivity and service status.
    """
    import time
    from fastapi import Response
    from api.jobs import redis_client as jobs_redis
    from agents.resume_versions import redis_client as versions_redis
    
    health_status = {
        "status": "ok",
        "timestamp": time.time(),
        "services": {}
    }
    
    overall_healthy = True
    
    # Check Redis for jobs
    try:
        if jobs_redis:
            jobs_redis.ping()
            health_status["services"]["redis_jobs"] = "healthy"
        else:
            health_status["services"]["redis_jobs"] = "unavailable"
            overall_healthy = False
    except Exception as e:
        health_status["services"]["redis_jobs"] = f"unhealthy: {str(e)}"
        overall_healthy = False
    
    # Check Redis for versions
    try:
        if versions_redis:
            versions_redis.ping()
            health_status["services"]["redis_versions"] = "healthy"
        else:
            health_status["services"]["redis_versions"] = "unavailable"
            overall_healthy = False
    except Exception as e:
        health_status["services"]["redis_versions"] = f"unhealthy: {str(e)}"
        overall_healthy = False
    
    # Check LLM availability (basic check)
    try:
        from core.llm import fast_llm_call
        # Just check if the function exists and can be called
        health_status["services"]["llm"] = "available"
    except Exception as e:
        health_status["services"]["llm"] = f"unavailable: {str(e)}"
        overall_healthy = False
    
    if not overall_healthy:
        health_status["status"] = "degraded"
        from fastapi.responses import JSONResponse
        return JSONResponse(
            content=health_status,
            status_code=503
        )
    
    return health_status


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

    try:
        jd_text = (
            extract_text(job_description_file)
            if job_description_file
            else job_description_text
        )

        resume_text = extract_text(resume_file)
    except ValueError as e:
        # File size or type error
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Text extraction failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to extract text from files"
        )

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
@router.post("/ats/compare")
def compare_ats(
    job_description: str = Form(None),
    jd_file: UploadFile | None = File(None),
    resume: UploadFile = File(...),
):
    """
    Compare ATS scores before and after resume rewrite.
    
    Args:
        job_description: Job description text (optional if jd_file provided)
        jd_file: Job description file (optional if job_description provided)
        resume: Resume file (required)
    
    Returns:
        Comparison results with before/after scores and analysis
    """
    # -----------------------------
    # 1️⃣ Input validation
    # -----------------------------
    if not job_description and not jd_file:
        raise HTTPException(
            status_code=400,
            detail="JD text or JD file is required",
        )

    # -----------------------------
    # 2️⃣ Text extraction with file size validation
    # -----------------------------
    try:
        jd_text = extract_text(jd_file) if jd_file else job_description
        resume_text = extract_text(resume)
    except ValueError as e:
        # File size or type error
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Text extraction failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to extract text from files"
        )

    if not jd_text or not jd_text.strip():
        raise HTTPException(
            status_code=400,
            detail="Job description is empty or could not be extracted. "
                   "Please ensure your JD file contains readable text or provide JD text directly."
        )
    
    if not resume_text or not resume_text.strip():
        raise HTTPException(
            status_code=400,
            detail="Resume is empty or could not be extracted. "
                   "Please ensure your resume file is a valid PDF, DOCX, or TXT file with readable content."
        )

    # -----------------------------
    # 3️⃣ JD analysis (LLM – structured)
    # -----------------------------
    jd_data = analyze_jd(jd_text)

    raw_jd_keywords = {
        "required_skills": jd_data.get("required_skills", []),
        "optional_skills": jd_data.get("optional_skills", []),
        "tools": jd_data.get("tools", []),
    }

    # ✅ Canonical JD normalization (FIX 2)
    jd_keywords_all = normalize_jd_keywords(raw_jd_keywords)

    # -----------------------------
    # 🧠 4️⃣ Role auto-detection
    # -----------------------------
    role_info = detect_role(jd_text, resume_text)
    role = role_info["role"]

    # -----------------------------
    # 5️⃣ Keyword confidence (resume vs JD)
    # -----------------------------
    confidence = keyword_confidence(
        jd_keywords_all,
        resume_text,
    )

    # -----------------------------
    # 6️⃣ Deterministic safe skill inference
    # -----------------------------
    inferred_skills = infer_skills_from_resume(
        resume_text=resume_text,
        explicit_skills=(
            jd_keywords_all["required_skills"]
            + jd_keywords_all["optional_skills"]
            + jd_keywords_all["tools"]
        ),
    )

    # 🎯 Role-aware confidence tuning
    inferred_skills = tune_confidence_by_role(
        inferred_skills,
        role=role,
    )

    # -----------------------------
    # 7️⃣ SAFE keywords allowed for rewrite
    # -----------------------------
    safe_keywords = {
        "explicit": (
            confidence["high"]["required_skills"]
            + confidence["high"]["tools"]
        ),
        "derived": [
            {
                "skill": s["skill"],
                "confidence": s["confidence"],
                "evidence": s.get("evidence", []),
            }
            for s in inferred_skills
            if s["confidence"] >= 0.8
        ],
    }

    # -----------------------------
    # 8️⃣ ATS score BEFORE rewrite
    # -----------------------------
    before = score_detailed(
        jd_keywords_all,
        resume_text,
        inferred_skills=inferred_skills,  # ✅ evidence-gated scoring
    )

    # -----------------------------
    # 9️⃣ Rewrite resume (LLM – guarded)
    # -----------------------------
    try:
        rewritten = rewrite(
            safe_keywords,
            resume_text,
        )
        
        # Check if rewrite failed
        if rewritten.get("error"):
            logger = logging.getLogger(__name__)
            logger.warning(f"Resume rewrite had errors: {rewritten.get('error')}")
            # Continue with partial results if available
        
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Resume rewrite failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to rewrite resume. Please try again or contact support if the issue persists."
        )

    # Note: validate_rewrite is already called inside rewrite() function
    # No need to call it again here

    rewritten_text = (
        rewritten.get("summary", "")
        + "\n"
        + "\n".join(
            bullet
            for exp in rewritten.get("experience", [])
            for bullet in exp.get("bullets", [])
        )
    ).strip()

    # Fallback safety
    if not rewritten_text:
        logger = logging.getLogger(__name__)
        logger.warning("Rewritten text is empty, using original resume")
        rewritten_text = resume_text

    # -----------------------------
    # 🔟 ATS score AFTER rewrite
    # -----------------------------
    after = score_detailed(
        jd_keywords_all,
        rewritten_text,
        inferred_skills=inferred_skills,
    )

    # 🚨 ATS MONOTONICITY GUARD (MANDATORY)
    if after["score"] < before["score"]:
        after = before
        rewritten = {
            "summary": "",
            "experience": [],
            "skills": [],
            "note": "Rewrite skipped to prevent ATS regression",
        }

    # -----------------------------
    # 1️⃣1️⃣ JD fit classification
    # -----------------------------
    jd_fit = classify_jd_fit(after)

    # -----------------------------
    # 1️⃣2️⃣ Resume risk flags
    # -----------------------------
    resume_risks = resume_risk_flags(
        jd_keywords_all,
        after,
    )

    # -----------------------------
    # 1️⃣3️⃣ Keyword attribution (AFTER only)
    # -----------------------------
    keyword_attribution = attribute_keywords_to_bullets(
        jd_keywords_all,
        rewritten.get("experience", []),
    )

    # -----------------------------
    # 1️⃣4️⃣ ATS risk band
    # -----------------------------
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

    # -----------------------------
    # 1️⃣5️⃣ Improvement analysis
    # -----------------------------
    before_keywords = set(
        sum(before["matched_keywords"].values(), [])
    )
    after_keywords = set(
        sum(after["matched_keywords"].values(), [])
    )

    improvement = {
        "score_delta": after["score"] - before["score"],
        "newly_added_keywords": list(after_keywords - before_keywords),
    }

    # -----------------------------
    # 1️⃣6️⃣ Skill gap analysis (NEW)
    # -----------------------------
    from agents.skill_gap_analyzer import analyze_skill_gap
    
    skill_gap = analyze_skill_gap(
        jd_keywords_all,
        resume_text,
        inferred_skills
    )
    
    # -----------------------------
    # 1️⃣7️⃣ Visual comparison (NEW)
    # -----------------------------
    from agents.diff_viewer import diff_resume_structured
    from agents.resume_formatter import format_resume_text
    
    # Create structured resume objects for comparison
    before_resume_structured = {
        "summary": "",  # Original resume doesn't have structured format
        "experience": [],  # Would need parsing, but for now use text
        "skills": []
    }
    
    # For comparison, we'll use the formatted text versions
    before_resume_text = resume_text
    after_resume_text = format_resume_text(rewritten)
    
    # Create visual diff
    visual_diff = diff_resume_structured(
        {"summary": "", "experience": [], "skills": []},  # Simplified before
        rewritten  # Structured after
    )

    # -----------------------------
    # ✅ Final response
    # -----------------------------
    return {
        "role_detection": role_info,
        "before": before,
        "after": after,
        "improvement": improvement,
        "risk": risk,
        "keyword_attribution": keyword_attribution,
        "keyword_confidence": confidence,
        "resume_risks": resume_risks,
        "jd_fit": jd_fit,
        "inferred_skills": inferred_skills,  # 🔍 evidence trace
        "rewritten_resume": rewritten,
        "visual_comparison": visual_diff,  # 🆕 Visual before/after diff
        "skill_gap_analysis": skill_gap,  # 🆕 Skill gap analysis
    }

@router.post("/ats/batch")
def batch_process_jds(
    resume: UploadFile = File(...),
    jd_files: List[UploadFile] = File(...),
    resume_id: str = Form(None),
):
    """
    Process resume against multiple job descriptions at once.
    
    Args:
        resume: Resume file
        jd_files: List of job description files (up to 20)
        resume_id: Optional resume ID for tracking
    
    Returns:
        Batch processing results with scores and recommendations for each JD
    """
    from agents.batch_processor import process_batch_jds
    from api.schemas import BatchJDRequest
    
    # Validate number of JDs
    if len(jd_files) > 20:
        raise HTTPException(
            status_code=400,
            detail="Maximum 20 job descriptions allowed per batch"
        )
    
    if len(jd_files) == 0:
        raise HTTPException(
            status_code=400,
            detail="At least one job description file is required"
        )
    
    # Extract resume text
    try:
        resume_text = extract_text(resume)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to extract resume text: {str(e)}"
        )
    
    # Extract JD texts
    jd_list = []
    for idx, jd_file in enumerate(jd_files):
        try:
            jd_text = extract_text(jd_file)
            jd_id = jd_file.filename or f"jd_{idx}"
            jd_list.append({
                "jd_id": jd_id,
                "jd_text": jd_text,
                "title": jd_file.filename or f"Job {idx + 1}"
            })
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to extract JD {idx}: {e}")
            jd_list.append({
                "jd_id": f"jd_{idx}",
                "jd_text": "",
                "title": jd_file.filename or f"Job {idx + 1}",
                "error": str(e)
            })
    
    # Process batch
    try:
        results = process_batch_jds(
            resume_text=resume_text,
            jd_list=jd_list,
            resume_id=resume_id
        )
        return results
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Batch processing failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Batch processing failed: {str(e)}"
        )


@router.post("/ats/batch/text")
def batch_process_jds_text(
    resume: UploadFile = File(...),
    jd_texts: List[str] = Form(...),
    jd_titles: List[str] = Form(None),
    resume_id: str = Form(None),
):
    """
    Process resume against multiple job descriptions (text input).
    
    Args:
        resume: Resume file
        jd_texts: List of job description texts
        jd_titles: Optional list of job titles
        resume_id: Optional resume ID for tracking
    
    Returns:
        Batch processing results
    """
    from agents.batch_processor import process_batch_jds
    
    if len(jd_texts) > 20:
        raise HTTPException(
            status_code=400,
            detail="Maximum 20 job descriptions allowed per batch"
        )
    
    if len(jd_texts) == 0:
        raise HTTPException(
            status_code=400,
            detail="At least one job description is required"
        )
    
    # Extract resume text
    try:
        resume_text = extract_text(resume)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to extract resume text: {str(e)}"
        )
    
    # Prepare JD list
    jd_list = []
    titles = jd_titles or []
    
    for idx, jd_text in enumerate(jd_texts):
        jd_list.append({
            "jd_id": f"jd_{idx}",
            "jd_text": jd_text,
            "title": titles[idx] if idx < len(titles) else f"Job {idx + 1}"
        })
    
    # Process batch
    try:
        results = process_batch_jds(
            resume_text=resume_text,
            jd_list=jd_list,
            resume_id=resume_id
        )
        return results
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Batch processing failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Batch processing failed: {str(e)}"
        )


@router.get("/ats/compare/{job_id}/skill-gap")
def get_skill_gap_analysis(job_id: str):
    """
    Get skill gap analysis for a completed job.
    
    Args:
        job_id: Job ID from /ats/compare endpoint
    
    Returns:
        Skill gap analysis with missing skills and recommendations
    """
    job = get_job(job_id)
    if not job or job.get("status") != "completed":
        raise HTTPException(
            status_code=404,
            detail="Job not found or not completed"
        )
    
    result = job.get("result", {})
    if "skill_gap_analysis" in result:
        return result["skill_gap_analysis"]
    
    raise HTTPException(
        status_code=404,
        detail="Skill gap analysis not available for this job"
    )


@router.post("/resumes")
def create_resume_entry(
    title: str = Form(...),
    tags: str = Form(None),  # Comma-separated
    user_id: str = Form("default"),
):
    """
    Create a new resume entry in the management system.
    
    Args:
        title: Resume title/name
        tags: Comma-separated tags
        user_id: User identifier
    
    Returns:
        Resume ID and metadata
    """
    from agents.resume_manager import create_resume
    
    tag_list = [t.strip() for t in tags.split(",")] if tags else []
    
    try:
        resume_id = create_resume(
            resume_data={},  # Will be populated when resume is uploaded
            user_id=user_id,
            title=title,
            tags=tag_list
        )
        
        return {
            "resume_id": resume_id,
            "title": title,
            "tags": tag_list,
            "message": "Resume entry created. Upload resume content to associate with this entry."
        }
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to create resume entry: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create resume entry: {str(e)}"
        )


@router.get("/resumes")
def list_resume_entries(
    user_id: str = "default",
    tags: str = None,  # Comma-separated filter
):
    """List all resumes for a user."""
    from agents.resume_manager import list_resumes
    
    tag_list = [t.strip() for t in tags.split(",")] if tags else None
    
    try:
        resumes = list_resumes(user_id=user_id, tags=tag_list)
        return {
            "count": len(resumes),
            "resumes": resumes
        }
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to list resumes: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list resumes: {str(e)}"
        )


@router.get("/resumes/{resume_id}")
def get_resume_entry(resume_id: str):
    """Get resume metadata and associated applications."""
    from agents.resume_manager import get_resume, list_applications
    
    resume = get_resume(resume_id)
    if not resume:
        raise HTTPException(
            status_code=404,
            detail="Resume not found"
        )
    
    applications = list_applications(resume_id)
    
    return {
        **resume,
        "applications": applications
    }


@router.post("/resumes/{resume_id}/applications")
def create_application_entry(
    resume_id: str,
    jd_file: UploadFile = File(...),
    jd_title: str = Form(None),
    company: str = Form(None),
    status: str = Form("applied"),
    ats_score: int = Form(None),
    notes: str = Form(None),
):
    """
    Create an application record for a resume.
    
    Args:
        resume_id: Resume ID
        jd_file: Job description file
        jd_title: Job title
        company: Company name
        status: Application status
        ats_score: ATS score (optional)
        notes: Optional notes
    
    Returns:
        Application ID
    """
    from agents.resume_manager import create_application, get_resume
    
    # Verify resume exists
    resume = get_resume(resume_id)
    if not resume:
        raise HTTPException(
            status_code=404,
            detail="Resume not found"
        )
    
    # Extract JD text
    try:
        jd_text = extract_text(jd_file)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to extract JD text: {str(e)}"
        )
    
    try:
        application_id = create_application(
            resume_id=resume_id,
            jd_text=jd_text,
            jd_title=jd_title,
            company=company,
            status=status,
            ats_score=ats_score,
            notes=notes
        )
        
        return {
            "application_id": application_id,
            "resume_id": resume_id,
            "message": "Application created successfully"
        }
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to create application: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create application: {str(e)}"
        )


@router.patch("/applications/{application_id}")
def update_application(
    application_id: str,
    status: str = Form(None),
    notes: str = Form(None),
):
    """Update application status."""
    from agents.resume_manager import update_application_status
    
    if status not in ["applied", "interview", "rejected", "offer", "withdrawn"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid status. Must be: applied, interview, rejected, offer, withdrawn"
        )
    
    try:
        update_application_status(application_id, status, notes)
        return {"message": "Application updated successfully"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to update application: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update application: {str(e)}"
        )


@router.get("/dashboard")
def get_dashboard(user_id: str = "default"):
    """Get dashboard statistics and overview."""
    from agents.resume_manager import get_dashboard_stats
    
    try:
        stats = get_dashboard_stats(user_id)
        return stats
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to get dashboard: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get dashboard: {str(e)}"
        )


@router.get("/ats/compare/{job_id}/visual")
def get_visual_comparison(job_id: str):
    """
    Get visual before/after comparison for a completed job.
    
    Args:
        job_id: Job ID from /ats/compare endpoint
    
    Returns:
        Visual diff with structured changes
    """
    job = get_job(job_id)
    if not job or job.get("status") != "completed":
        raise HTTPException(
            status_code=404,
            detail="Job not found or not completed"
        )
    
    result = job.get("result", {})
    if "visual_comparison" in result:
        return result["visual_comparison"]
    
    # If visual comparison not stored, generate it
    from agents.diff_viewer import diff_resume_structured
    rewritten = result.get("rewritten_resume", {})
    before_resume = result.get("original_resume", {})
    
    visual_diff = diff_resume_structured(before_resume, rewritten)
    return visual_diff


@router.post("/ats/validate-format")
def validate_resume_format(
    resume_file: UploadFile = File(...),
):
    """
    Validate if a resume file is ATS-friendly.
    
    Args:
        resume_file: Resume file to validate (PDF or DOCX)
    
    Returns:
        Validation results with issues, warnings, and recommendations
    """
    from agents.ats_format_validator import validate_ats_format
    
    filename = resume_file.filename.lower()
    
    if filename.endswith(".pdf"):
        file_type = "pdf"
    elif filename.endswith(".docx"):
        file_type = "docx"
    else:
        raise HTTPException(
            status_code=400,
            detail="Only PDF and DOCX files can be validated for ATS format"
        )
    
    try:
        # Save file temporarily for validation
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_type}") as tmp_file:
            content = resume_file.file.read()
            tmp_file.write(content)
            tmp_path = tmp_file.name
        
        try:
            result = validate_ats_format(file_path=tmp_path, file_type=file_type)
            return result
        finally:
            # Clean up temp file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Format validation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to validate file format: {str(e)}"
        )


@router.post("/ats/download")
def download_resume(
    rewritten_resume: dict,  # Will validate with Pydantic if needed
    format: str = "docx",  # docx | txt | pdf
):
    """
    Download rewritten resume in specified format.
    
    Args:
        rewritten_resume: Resume data dictionary with summary, experience, skills
        format: Output format (docx, txt, or pdf)
    
    Returns:
        StreamingResponse with the resume file
    """
    from api.schemas import RewrittenResumeRequest
    
    # Validate request body
    try:
        validated = RewrittenResumeRequest(**rewritten_resume)
        rewritten_resume = validated.dict()
    except Exception as e:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid resume data: {str(e)}"
        )
    
    if format not in ["docx", "txt", "pdf"]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid format: {format}. Supported: docx, txt, pdf"
        )
    resume_text = format_resume_text(rewritten_resume)

    if format == "txt":
        return StreamingResponse(
            iter([resume_text]),
            media_type="text/plain",
            headers={
                "Content-Disposition": "attachment; filename=resume.txt"
            },
        )

    if format == "pdf":
        # Use resume_exporter for BytesIO streaming
        from agents.resume_exporter import export_pdf as export_pdf_stream
        buffer = export_pdf_stream(resume_text)
        return StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers={
                "Content-Disposition": "attachment; filename=resume.pdf"
            },
        )

    # default → DOCX
    # Use resume_exporter for BytesIO streaming
    from agents.resume_exporter import export_docx as export_docx_stream
    buffer = export_docx_stream(resume_text)
    
    # Optional: Validate format before returning
    # Note: This would require saving to temp file, validating, then streaming
    # For now, we'll skip validation on download to avoid performance impact
    
    return StreamingResponse(
        buffer,
        media_type=(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ),
        headers={
            "Content-Disposition": "attachment; filename=resume.docx"
        },
    )


@router.get("/ats/templates")
def list_templates():
    return [
        {
            "id": k,
            "name": v["name"],
        }
        for k, v in TEMPLATES.items()
    ]


@router.post("/ats/download/pdf")
def download_pdf(
    rewritten_resume: dict,
    template_id: str = "classic",
):
    sections = format_resume_sections(rewritten_resume)

    buffer = render_pdf(
        resume_sections=sections,
        template_id=template_id,
    )

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f"attachment; filename=resume_{template_id}.pdf"
            )
        },
    )


@router.post("/ats/download/zip")
def download_zip(
    rewritten_resume: dict,
    template_id: str = "classic",
):
    buffer = export_zip(
        rewritten_resume=rewritten_resume,
        template_id=template_id,
    )

    return StreamingResponse(
        buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": (
                "attachment; filename=resume_bundle.zip"
            )
        },
    )

@router.post("/ats/templates/recommend")
def recommend_resume_templates(role_info: dict):
    """
    Recommend resume templates based on role information.
    
    Args:
        role_info: Dictionary with role, confidence, and signals
    
    Returns:
        List of recommended template IDs and names
    """
    from api.schemas import RoleInfoRequest
    
    # Validate request body
    try:
        validated = RoleInfoRequest(**role_info)
        role_info = validated.dict()
    except Exception as e:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid role info: {str(e)}"
        )
    
    ids = recommend_templates(role_info)

    return [
        {
            "id": t,
            "name": TEMPLATES[t]["name"],
        }
        for t in ids
    ]


def get_approved_resume(resume_id: str) -> dict | None:
    """
    Retrieves an approved resume version by ID.
    For now, returns the current version if it exists.
    TODO: Implement proper approval workflow with Redis/database.
    """
    try:
        version = get_current_version()
        if version and version.get("resume"):
            return version["resume"]
        return None
    except (IndexError, KeyError):
        return None


@router.get("/resume/{resume_id}/export")
def export_resume(
    resume_id: str,
    format: str = "pdf",   # pdf | docx | txt | zip
):
    # 🔒 MUST be approved version
    resume = get_approved_resume(resume_id)

    if not resume:
        raise HTTPException(404, "Resume not approved yet")

    tmp = tempfile.NamedTemporaryFile(delete=False)

    if format == "pdf":
        # Use exporters/pdf_exporter for file path writing
        from agents.exporters.pdf_exporter import export_pdf
        export_pdf(resume, tmp.name)
        return FileResponse(tmp.name, filename="resume.pdf")

    if format == "docx":
        # Use exporters/docx_exporter for file path writing
        from agents.exporters.docx_exporter import export_docx
        export_docx(resume, tmp.name)
        return FileResponse(tmp.name, filename="resume.docx")

    if format == "txt":
        content = export_txt(resume)
        with open(tmp.name, "w") as f:
            f.write(content)
        return FileResponse(tmp.name, filename="resume.txt")

    if format == "zip":
        export_zip(resume, tmp.name)
        return FileResponse(tmp.name, filename="resume.zip")

    raise HTTPException(400, "Invalid export format")
