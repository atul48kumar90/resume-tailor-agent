# api/routes.py
from fastapi import (
    APIRouter,
    UploadFile,
    File,
    Form,
    HTTPException,
    Body,
)
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

import logging
import asyncio

from api.files import extract_text, extract_text_async
from api.jobs import (
    create_job,
    get_job,
    update_job,
    fail_job,
)
from core.security import (
    sanitize_text,
    sanitize_jd_text,
    sanitize_resume_text,
    validate_user_id,
    validate_job_id,
    validate_tags,
    validate_persona,
)

from agents.jd_analyzer import analyze_jd
from agents.resume_rewriter import rewrite
from agents.ats_scorer import (
    score_detailed,
    attribute_keywords_to_bullets,
)
from agents.ats_scorer_advanced import (
    score_detailed_advanced,
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
from api.schemas import ParsedResumeResponse
import tempfile




router = APIRouter()


# ============================================================
# Resume Parsing Endpoint
# ============================================================

@router.post("/resume/parse", response_model=ParsedResumeResponse)
async def parse_resume_endpoint(
    resume: UploadFile = File(...),
):
    """
    Parse resume and extract structured information.
    
    Extracts:
    - Contact information (name, email, phone, LinkedIn, etc.)
    - Education (institutions, degrees, dates, GPA)
    - Work experience (companies, titles, dates, locations, descriptions)
    - Certifications
    - Skills
    - Projects
    - Languages
    - Awards
    
    Args:
        resume: Resume file (PDF, DOCX, or TXT)
    
    Returns:
        Structured resume data
    """
    from api.files import extract_text_async
    from agents.resume_parser import parse_resume_async
    
    try:
        # Extract text from file
        resume_text = await extract_text_async(resume)
        
        # Parse resume
        parsed_data = await parse_resume_async(resume_text, use_cache=True)
        
        return ParsedResumeResponse(**parsed_data)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Resume parsing failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to parse resume: {str(e)}"
        )


@router.post("/resume/parse/text", response_model=ParsedResumeResponse)
async def parse_resume_text_endpoint(
    resume_text: str = Form(...),
):
    """
    Parse resume from text input.
    
    Args:
        resume_text: Resume text content
    
    Returns:
        Structured resume data
    """
    from core.security import sanitize_resume_text
    from agents.resume_parser import parse_resume_async
    from api.schemas import ParsedResumeResponse
    
    try:
        # Sanitize input
        resume_text = sanitize_resume_text(resume_text)
        
        # Parse resume
        parsed_data = await parse_resume_async(resume_text, use_cache=True)
        
        return ParsedResumeResponse(**parsed_data)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Resume parsing failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to parse resume: {str(e)}"
        )


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

def process_resume_job(job_id: str, jd: str, resume: str, persona: str, parsed_resume_data: Optional[Dict[str, Any]] = None):
    logger = logging.getLogger(__name__)
    logger.info(f"Processing job {job_id}")

    try:
        from agents.ats_scorer import score_detailed
        from agents.recruiter_persona import tune

        jd_data = analyze_jd(jd)
        
        # Convert JD data to format expected by rewrite() function
        # rewrite() expects: {"explicit": [...], "derived": [...]}
        ats_keywords = jd_data.get("ats_keywords", {})
        if isinstance(ats_keywords, dict):
            # Extract all keywords from the dict structure
            all_keywords = (
                ats_keywords.get("required_skills", [])
                + ats_keywords.get("optional_skills", [])
                + ats_keywords.get("tools", [])
            )
            jd_keywords_for_rewrite = {
                "explicit": all_keywords,
                "derived": [],  # No derived keywords in simple rewrite
            }
        else:
            # Fallback if ats_keywords is not a dict
            jd_keywords_for_rewrite = {
                "explicit": [],
                "derived": [],
            }
        
        # Calculate BEFORE score (on original resume) - using advanced scorer
        before_ats = score_detailed_advanced(
            jd_data.get("ats_keywords", {}),
            resume,
            jd_data=jd_data,
            inferred_skills=None,
            parsed_resume_data=parsed_resume_data,
            enable_semantic=False,  # Disable semantic for performance in background jobs
        )
        
        # Pass baseline keywords to rewrite function so it knows what to preserve
        baseline_keywords = before_ats.get("matched_keywords", {})
        
        # Try rewrite with baseline keywords (to preserve existing matches)
        rewritten = rewrite(
            jd_keywords_for_rewrite, 
            resume,
            baseline_keywords=baseline_keywords
        )
        
        # Merge rewritten sections with preserved sections from parsed resume
        # This ensures contact info, education, certifications, etc. are preserved
        if parsed_resume_data:
            # Merge experience: use rewritten bullets but preserve company, title, dates from parsed data
            merged_experience = []
            parsed_experience = parsed_resume_data.get("experience", [])
            rewritten_experience = rewritten.get("experience", [])
            
            # Track which rewritten experiences have been matched to avoid duplicates
            matched_rewritten_indices = set()
            
            # Match rewritten experience entries with parsed experience by company/title
            for parsed_exp in parsed_experience:
                # Try to find matching rewritten experience entry
                matching_rewritten = None
                matching_index = None
                
                for idx, rewritten_exp in enumerate(rewritten_experience):
                    if idx in matched_rewritten_indices:
                        continue  # Skip already matched entries
                    
                    # Normalize strings for comparison
                    parsed_company = (parsed_exp.get("company") or "").lower().strip()
                    parsed_title = (parsed_exp.get("title") or "").lower().strip()
                    rewritten_title = (rewritten_exp.get("title") or "").lower().strip()
                    
                    # Extract company from rewritten title if it's in format "title | company"
                    rewritten_company = ""
                    if "|" in rewritten_title:
                        parts = rewritten_title.split("|")
                        if len(parts) == 2:
                            rewritten_company = parts[1].strip()
                            rewritten_title_only = parts[0].strip()
                        else:
                            rewritten_title_only = rewritten_title
                    else:
                        rewritten_title_only = rewritten_title
                    
                    # Match by company (more reliable)
                    if parsed_company and rewritten_company:
                        # Check if companies match (fuzzy match - one contains the other)
                        if (parsed_company in rewritten_company or rewritten_company in parsed_company or
                            parsed_company.replace(" ", "") == rewritten_company.replace(" ", "")):
                            matching_rewritten = rewritten_exp
                            matching_index = idx
                            break
                    
                    # Match by title if company match fails
                    if not matching_rewritten and parsed_title and rewritten_title_only:
                        # Check if titles are similar (fuzzy match)
                        if (parsed_title in rewritten_title_only or rewritten_title_only in parsed_title or
                            parsed_title.replace(" ", "") == rewritten_title_only.replace(" ", "")):
                            matching_rewritten = rewritten_exp
                            matching_index = idx
                            break
                    
                    # Fallback: check if parsed company is in rewritten title
                    if not matching_rewritten and parsed_company and rewritten_title:
                        if parsed_company in rewritten_title:
                            matching_rewritten = rewritten_exp
                            matching_index = idx
                            break
                
                # Merge: use parsed metadata (company, title, dates, location) with rewritten bullets
                merged_exp = {
                    "company": parsed_exp.get("company", ""),
                    "title": parsed_exp.get("title", ""),
                    "start_date": parsed_exp.get("start_date", ""),
                    "end_date": parsed_exp.get("end_date", ""),
                    "location": parsed_exp.get("location", ""),
                    "description": parsed_exp.get("description", ""),
                    "bullets": matching_rewritten.get("bullets", []) if matching_rewritten else parsed_exp.get("bullets", []),
                    "is_current": parsed_exp.get("is_current", False),
                }
                merged_experience.append(merged_exp)
                
                # Mark this rewritten experience as matched
                if matching_index is not None:
                    matched_rewritten_indices.add(matching_index)
            
            # Only add rewritten experiences that don't match any parsed experience
            # (This handles edge cases where LLM generated new experience entries)
            for idx, rewritten_exp in enumerate(rewritten_experience):
                if idx in matched_rewritten_indices:
                    continue  # Already matched and merged
                
                # Check if this rewritten exp is already in merged_experience by title/company
                already_merged = False
                rewritten_title_lower = (rewritten_exp.get("title") or "").lower()
                
                for merged_exp in merged_experience:
                    merged_title_lower = (merged_exp.get("title") or "").lower()
                    merged_company_lower = (merged_exp.get("company") or "").lower()
                    
                    # Check if rewritten title matches merged title or company
                    if (rewritten_title_lower and merged_title_lower and 
                        (rewritten_title_lower in merged_title_lower or merged_title_lower in rewritten_title_lower)):
                        already_merged = True
                        break
                    if (rewritten_title_lower and merged_company_lower and 
                        rewritten_title_lower in merged_company_lower):
                        already_merged = True
                        break
                
                if not already_merged:
                    # Extract company and title from rewritten entry if in format "title | company"
                    rewritten_title = rewritten_exp.get("title", "")
                    rewritten_company = ""
                    if "|" in rewritten_title:
                        parts = rewritten_title.split("|")
                        if len(parts) == 2:
                            rewritten_title = parts[0].strip()
                            rewritten_company = parts[1].strip()
                    
                    # Add as new entry (rare case - only if LLM generated something not in parsed data)
                    merged_experience.append({
                        "company": rewritten_company,
                        "title": rewritten_title,
                        "start_date": "",
                        "end_date": "",
                        "location": "",
                        "description": "",
                        "bullets": rewritten_exp.get("bullets", []),
                        "is_current": False,
                    })
            
            final_resume = {
                # Preserve contact information
                "contact": parsed_resume_data.get("contact", {}),
                # Use rewritten summary if available, otherwise use parsed summary
                "summary": rewritten.get("summary") or parsed_resume_data.get("summary", ""),
                # Use merged experience (parsed metadata + rewritten bullets)
                "experience": merged_experience,
                # Preserve education
                "education": parsed_resume_data.get("education", []),
                # Use rewritten skills (with JD-relevant keywords), fallback to parsed if empty
                "skills": rewritten.get("skills", []) or parsed_resume_data.get("skills", []),
                # Preserve all other sections
                "certifications": parsed_resume_data.get("certifications", []),
                "projects": parsed_resume_data.get("projects", []),
                "languages": parsed_resume_data.get("languages", []),
                "awards": parsed_resume_data.get("awards", []),
            }
        else:
            # Fallback: if no parsed data, use rewritten data and add empty sections
            final_resume = {
                "contact": {},
                "summary": rewritten.get("summary", ""),
                "experience": rewritten.get("experience", []),
                "education": [],
                "skills": rewritten.get("skills", []),
                "certifications": [],
                "projects": [],
                "languages": [],
                "awards": [],
            }
        
        final = tune(final_resume, persona)
        
        # Calculate AFTER score (on final tuned resume)
        # Format final resume to text for scoring
        from agents.resume_formatter import format_resume_text
        rewritten_text = format_resume_text(final)
        
        after_ats = score_detailed_advanced(
            jd_data.get("ats_keywords", {}),
            rewritten_text,
            jd_data=jd_data,
            inferred_skills=None,
            parsed_resume_data=parsed_resume_data,
            enable_semantic=False,  # Disable semantic for performance in background jobs
        )
        
        # 🚨 SMART ATS MONOTONICITY GUARD - Prevent regression but allow improvements
        # Strategy:
        # - If before score is already good (>50), be strict: prevent ANY regression
        # - If before score is low (<50), be lenient: allow rewrite if it adds keywords or improves coverage
        before_score = before_ats["score"]
        after_score = after_ats["score"]
        
        # Count keywords matched
        before_keywords_count = (
            len(before_ats.get("matched_keywords", {}).get("required_skills", []))
            + len(before_ats.get("matched_keywords", {}).get("tools", []))
            + len(before_ats.get("matched_keywords", {}).get("optional_skills", []))
        )
        after_keywords_count = (
            len(after_ats.get("matched_keywords", {}).get("required_skills", []))
            + len(after_ats.get("matched_keywords", {}).get("tools", []))
            + len(after_ats.get("matched_keywords", {}).get("optional_skills", []))
        )
        
        should_reject = False
        if after_score < before_score:
            if before_score >= 50:
                # Strict: prevent regression if score is already good
                should_reject = True
                logger.warning(
                    f"Job {job_id}: After score ({after_score}) < Before score ({before_score}). "
                    f"Rejecting rewrite to prevent regression (before score was good)."
                )
            elif after_keywords_count < before_keywords_count:
                # Lenient but still check: if we lost keywords, reject
                should_reject = True
                logger.warning(
                    f"Job {job_id}: After score ({after_score}) < Before score ({before_score}) "
                    f"AND lost keywords ({after_keywords_count} < {before_keywords_count}). "
                    f"Rejecting rewrite."
                )
            else:
                # Score decreased but keywords increased - allow it (might be temporary during optimization)
                logger.info(
                    f"Job {job_id}: After score ({after_score}) < Before score ({before_score}) "
                    f"but keywords increased ({after_keywords_count} > {before_keywords_count}). "
                    f"Allowing rewrite (low before score, improving keywords)."
                )
        
        if should_reject:
            # Use original resume if rewrite decreased score
            after_ats = before_ats
            final = {
                "contact": parsed_resume_data.get("contact", {}) if parsed_resume_data else {},
                "summary": parsed_resume_data.get("summary", "") if parsed_resume_data else "",
                "experience": parsed_resume_data.get("experience", []) if parsed_resume_data else [],
                "education": parsed_resume_data.get("education", []) if parsed_resume_data else [],
                "skills": parsed_resume_data.get("skills", []) if parsed_resume_data else [],
                "certifications": parsed_resume_data.get("certifications", []) if parsed_resume_data else [],
                "projects": parsed_resume_data.get("projects", []) if parsed_resume_data else [],
                "languages": parsed_resume_data.get("languages", []) if parsed_resume_data else [],
                "awards": parsed_resume_data.get("awards", []) if parsed_resume_data else [],
                "note": "Rewrite skipped to prevent ATS score regression",
            }

        # Calculate skill gap analysis
        skill_gap_analysis = None
        try:
            from agents.skill_gap_analyzer import analyze_skill_gap
            from agents.skill_inference import infer_skills_from_resume
            
            # Infer skills from original resume
            inferred_skills = infer_skills_from_resume(
                resume_text=resume,
                explicit_skills=(
                    jd_data.get("ats_keywords", {}).get("required_skills", [])
                    + jd_data.get("ats_keywords", {}).get("optional_skills", [])
                    + jd_data.get("ats_keywords", {}).get("tools", [])
                ),
            )
            
            # Get explicit skills from parsed resume data if available
            explicit_skills = None
            if parsed_resume_data:
                explicit_skills = parsed_resume_data.get("skills", [])
            
            skill_gap_analysis = analyze_skill_gap(
                jd_data.get("ats_keywords", {}),
                resume,
                inferred_skills=inferred_skills,
                explicit_skills=explicit_skills
            )
        except Exception as e:
            logger.warning(f"Failed to calculate skill gap analysis: {e}")

        # Collect rejected skills from rewrite (if any)
        rejected_skills = rewritten.get("_rejected_skills", [])
        
        # Get missing skills from skill gap analysis
        missing_skills = []
        if skill_gap_analysis:
            missing_skills_dict = skill_gap_analysis.get("missing_skills", {})
            missing_skills.extend(missing_skills_dict.get("required_skills", []))
            missing_skills.extend(missing_skills_dict.get("optional_skills", []))
            missing_skills.extend(missing_skills_dict.get("tools", []))
        
        # Combine rejected skills and missing skills (remove duplicates and normalize)
        # Prefer JD terminology when deduplicating
        from agents.skill_normalizer import merge_skill_lists
        # Get all JD skills as preferred forms
        all_jd_skills = []
        jd_keywords = jd_data.get("ats_keywords", {})
        all_jd_skills.extend(jd_keywords.get("required_skills", []))
        all_jd_skills.extend(jd_keywords.get("optional_skills", []))
        all_jd_skills.extend(jd_keywords.get("tools", []))
        
        all_pending_skills = merge_skill_lists(
            rejected_skills, 
            missing_skills,
            preferred_skills=all_jd_skills
        )
        
        job_result = {
            "resume": final,
            "original_resume": resume,  # Store original resume text for comparison
            "ats": {
                "before": before_ats,
                "after": after_ats,
            },
            "skill_gap_analysis": skill_gap_analysis,  # Store skill gap analysis
            "jd_analysis": jd_data,
            "parsed_resume_data": parsed_resume_data,  # Store parsed data in job result
            "pending_skills_approval": all_pending_skills,  # Skills needing user approval
            "needs_approval": len(all_pending_skills) > 0,  # Flag to show approval UI
        }
        
        # Store in both Redis (for our tracking) and return for RQ
        update_job(job_id, job_result)
        
        # Return result so RQ stores it (this makes job.result available and marks job as finished)
        logger.info(f"Job {job_id} completed successfully. Before: {before_score}, After: {after_score}")
        return job_result

    except Exception as e:
        logger.exception(f"Unhandled error while processing job {job_id}")
        fail_job(job_id, str(e))
        # Re-raise so RQ marks job as failed
        raise


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
    job_description_text: str | None = Form(None),
    job_description_file: UploadFile | None = File(None),
    resume_file: UploadFile = File(...),
    recruiter_persona: str = Form("general"),
):
    """
    Tailor resume to job description using background job queue.
    """
    logger = logging.getLogger(__name__)
    from core.job_queue import enqueue_job
    
    # Sanitize inputs
    try:
        recruiter_persona = validate_persona(recruiter_persona)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
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
            else sanitize_jd_text(job_description_text)  # Sanitize text input
        )

        resume_text = extract_text(resume_file)
        
        # Sanitize extracted text
        resume_text = sanitize_resume_text(resume_text)
        if jd_text and not job_description_file:
            jd_text = sanitize_jd_text(jd_text)
        
        # Parse resume for structured data (async, non-blocking)
        parsed_resume_data = None
        try:
            from agents.resume_parser import parse_resume
            parsed_resume_data = parse_resume(resume_text, use_cache=True)
            logger.info(f"Parsed resume: {len(parsed_resume_data.get('experience', []))} experiences, "
                       f"{len(parsed_resume_data.get('skills', []))} skills")
        except Exception as e:
            logger.warning(f"Resume parsing failed (continuing without structured data): {e}")
            parsed_resume_data = None
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

    # Parse resume for structured data (async, non-blocking)
    parsed_resume_data = None
    try:
        from agents.resume_parser import parse_resume
        parsed_resume_data = parse_resume(resume_text, use_cache=True)
        logger.info(f"Parsed resume: {len(parsed_resume_data.get('experience', []))} experiences, "
                   f"{len(parsed_resume_data.get('skills', []))} skills")
    except Exception as e:
        logger.warning(f"Resume parsing failed (continuing without structured data): {e}")
        parsed_resume_data = None

    # Enqueue job using RQ
    rq_job = enqueue_job(
        process_resume_job,
        job_id,
        jd_text,
        resume_text,
        recruiter_persona,
        parsed_resume_data,  # Pass parsed data as positional argument
        queue_name="default",
        job_id=job_id,  # Use same job_id for tracking
        job_timeout="15m",  # 15 minutes timeout for resume processing
    )
    
    if not rq_job:
        # Fallback: mark job as failed if queue unavailable
        fail_job(job_id, "Job queue unavailable")
        raise HTTPException(
            status_code=503,
            detail="Job queue service unavailable. Please try again later."
        )

    return {
        "job_id": job_id,
        "status": "queued",
        "queue_position": rq_job.get_position() if rq_job else None,
    }


# ------------------------
# File-Only Convenience Endpoint
# ------------------------

@router.post("/tailor/files")
def tailor_files(
    job_description: UploadFile = File(...),
    resume: UploadFile = File(...),
    recruiter_persona: str = Form("general"),
):
    jd_text = extract_text(job_description)
    resume_text = extract_text(resume)

    from core.job_queue import enqueue_job
    
    job_id = create_job()

    # Enqueue job using RQ
    rq_job = enqueue_job(
        process_resume_files_job,
        job_id,
        jd_text,
        resume_text,
        recruiter_persona,
        queue_name="default",
        job_id=job_id,
        job_timeout="15m",
    )
    
    if not rq_job:
        fail_job(job_id, "Job queue unavailable")
        raise HTTPException(
            status_code=503,
            detail="Job queue service unavailable. Please try again later."
        )

    return {
        "job_id": job_id,
        "status": "queued",
        "queue_position": rq_job.get_position() if rq_job else None,
    }


# ------------------------
# Job Status Endpoint
# ------------------------

@router.get("/jobs/{job_id}")
def job_status(job_id: str):
    """
    Get job status from both RQ and our job tracking.
    
    Job ID is validated to prevent injection attacks.
    """
    from core.job_queue import get_job_status
    
    # Validate job ID format
    try:
        job_id = validate_job_id(job_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Try to get status from RQ first (more detailed)
    rq_status = get_job_status(job_id)
    
    # Also get our internal job tracking
    job = get_job(job_id)
    
    # Merge statuses (RQ takes precedence for status)
    if rq_status:
        # Normalize status: RQ uses "finished" but we want "completed" for consistency
        rq_status_value = rq_status.get("status", "unknown")
        if rq_status_value == "finished":
            rq_status_value = "completed"
        
        result = {
            "job_id": job_id,
            "status": rq_status_value,
            "created_at": rq_status.get("created_at"),
            "started_at": rq_status.get("started_at"),
            "ended_at": rq_status.get("ended_at"),
        }
        
        # Add result/error from either source
        # If we have a Redis job update (from approve_skills), prioritize it over RQ
        # Check if Redis job has needs_approval=False (indicates recent update)
        if job and job.get("result") and job.get("result", {}).get("needs_approval") is False:
            # This is a recently updated result (from approve_skills), use it
            result["result"] = job["result"]
        elif rq_status.get("result"):
            result["result"] = rq_status["result"]
        elif job and job.get("result"):
            result["result"] = job["result"]
        
        if rq_status.get("error"):
            result["error"] = rq_status["error"]
        elif job and job.get("error"):
            result["error"] = job["error"]
        
        # Ensure status is "completed" if we have a result (for polling to stop)
        if result.get("result") and rq_status_value in ["finished", "completed"]:
            result["status"] = "completed"
        
        # Log for debugging
        logger = logging.getLogger(__name__)
        logger.debug(f"Job {job_id} status: {result.get('status')}, has_result: {bool(result.get('result'))}")
        
        return result
    
    # Fallback to internal job tracking
    if job:
        # If RQ job doesn't exist but internal job does, it might not be enqueued
        status = job.get("status", "unknown")
        if status == "pending":
            # Check if worker is running
            from core.job_queue import get_queue_stats
            queue_stats = get_queue_stats()
            if queue_stats.get("active_workers", 0) == 0:
                result = dict(job)
                result["warning"] = "Job is pending but no workers are running. Start worker with: ./scripts/start_worker.sh"
                return result
            else:
                result = dict(job)
                result["warning"] = "Job is pending but not found in RQ queue. It may not have been enqueued successfully."
                return result
        return job
    
    raise HTTPException(status_code=404, detail="Job not found")


class SkillApprovalRequest(BaseModel):
    approved_skills: List[str]


@router.post("/jobs/{job_id}/approve-skills")
def approve_skills(
    job_id: str,
    request: SkillApprovalRequest,
):
    """
    Approve skills and regenerate resume with approved skills.
    
    Args:
        job_id: Job ID from /tailor or /tailor/files endpoint
        approved_skills: List of skills user approved to add
    
    Returns:
        Updated job result with approved skills incorporated
    """
    from core.job_queue import get_job_status
    from agents.resume_rewriter import rewrite
    from agents.ats_scorer import score_detailed
    from agents.recruiter_persona import tune
    from agents.resume_formatter import format_resume_text
    import logging
    
    logger = logging.getLogger(__name__)
    
    # Validate job ID format
    try:
        job_id = validate_job_id(job_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Get job result
    rq_status = get_job_status(job_id)
    job = get_job(job_id)
    
    result = None
    if rq_status and rq_status.get("result"):
        result = rq_status["result"]
    elif job and job.get("result"):
        result = job["result"]
    
    if not result:
        raise HTTPException(
            status_code=404,
            detail="Job not found or not completed"
        )
    
    # Get original data
    original_resume = result.get("original_resume")
    jd_analysis = result.get("jd_analysis", {})
    parsed_resume_data = result.get("parsed_resume_data")
    
    if not original_resume:
        raise HTTPException(
            status_code=400,
            detail="Original resume not found in job result"
        )
    
    # Prepare JD keywords for rewrite
    ats_keywords = jd_analysis.get("ats_keywords", {})
    all_keywords = (
        ats_keywords.get("required_skills", [])
        + ats_keywords.get("optional_skills", [])
        + ats_keywords.get("tools", [])
    )
    jd_keywords_for_rewrite = {
        "explicit": all_keywords,
        "derived": [],
    }
    
    # Get baseline keywords (from before score)
    before_ats = result.get("ats", {}).get("before", {})
    baseline_keywords = before_ats.get("matched_keywords", {})
    
    # Get approved skills from request
    approved_skills = request.approved_skills
    
    # Re-run rewrite with approved skills
    logger.info(f"Re-running rewrite for job {job_id} with {len(approved_skills)} approved skills")
    rewritten = rewrite(
        jd_keywords_for_rewrite,
        original_resume,
        baseline_keywords=baseline_keywords,
        approved_skills=approved_skills,
    )
    
    # Merge rewritten sections (same logic as process_resume_job)
    if parsed_resume_data:
        merged_experience = []
        parsed_experience = parsed_resume_data.get("experience", [])
        rewritten_experience = rewritten.get("experience", [])
        
        # Track which rewritten experiences have been matched to avoid duplicates
        matched_rewritten_indices = set()
        
        for parsed_exp in parsed_experience:
            matching_rewritten = None
            matching_index = None
            
            for idx, rewritten_exp in enumerate(rewritten_experience):
                if idx in matched_rewritten_indices:
                    continue  # Skip already matched entries
                
                # Normalize strings for comparison
                parsed_company = (parsed_exp.get("company") or "").lower().strip()
                parsed_title = (parsed_exp.get("title") or "").lower().strip()
                rewritten_title = (rewritten_exp.get("title") or "").lower().strip()
                
                # Extract company from rewritten title if it's in format "title | company"
                rewritten_company = ""
                if "|" in rewritten_title:
                    parts = rewritten_title.split("|")
                    if len(parts) == 2:
                        rewritten_company = parts[1].strip()
                        rewritten_title_only = parts[0].strip()
                    else:
                        rewritten_title_only = rewritten_title
                else:
                    rewritten_title_only = rewritten_title
                
                # Match by company (more reliable)
                if parsed_company and rewritten_company:
                    # Check if companies match (fuzzy match - one contains the other)
                    if (parsed_company in rewritten_company or rewritten_company in parsed_company or
                        parsed_company.replace(" ", "") == rewritten_company.replace(" ", "")):
                        matching_rewritten = rewritten_exp
                        matching_index = idx
                        break
                
                # Match by title if company match fails
                if not matching_rewritten and parsed_title and rewritten_title_only:
                    # Check if titles are similar (fuzzy match)
                    if (parsed_title in rewritten_title_only or rewritten_title_only in parsed_title or
                        parsed_title.replace(" ", "") == rewritten_title_only.replace(" ", "")):
                        matching_rewritten = rewritten_exp
                        matching_index = idx
                        break
                
                # Fallback: check if parsed company is in rewritten title
                if not matching_rewritten and parsed_company and rewritten_title:
                    if parsed_company in rewritten_title:
                        matching_rewritten = rewritten_exp
                        matching_index = idx
                        break
            
            merged_exp = {
                "company": parsed_exp.get("company", ""),
                "title": parsed_exp.get("title", ""),
                "start_date": parsed_exp.get("start_date", ""),
                "end_date": parsed_exp.get("end_date", ""),
                "location": parsed_exp.get("location", ""),
                "description": parsed_exp.get("description", ""),
                "bullets": matching_rewritten.get("bullets", []) if matching_rewritten else parsed_exp.get("bullets", []),
                "is_current": parsed_exp.get("is_current", False),
            }
            merged_experience.append(merged_exp)
            
            # Mark this rewritten experience as matched
            if matching_index is not None:
                matched_rewritten_indices.add(matching_index)
        
        # Only add unmatched rewritten experiences (should be rare)
        for idx, rewritten_exp in enumerate(rewritten_experience):
            if idx in matched_rewritten_indices:
                continue  # Already matched and merged
            
            # Check if already merged
            already_merged = False
            rewritten_title_lower = (rewritten_exp.get("title") or "").lower()
            
            for merged_exp in merged_experience:
                merged_title_lower = (merged_exp.get("title") or "").lower()
                merged_company_lower = (merged_exp.get("company") or "").lower()
                
                if (rewritten_title_lower and merged_title_lower and 
                    (rewritten_title_lower in merged_title_lower or merged_title_lower in rewritten_title_lower)):
                    already_merged = True
                    break
                if (rewritten_title_lower and merged_company_lower and 
                    rewritten_title_lower in merged_company_lower):
                    already_merged = True
                    break
            
            if not already_merged:
                # Extract company and title from rewritten entry if in format "title | company"
                rewritten_title = rewritten_exp.get("title", "")
                rewritten_company = ""
                if "|" in rewritten_title:
                    parts = rewritten_title.split("|")
                    if len(parts) == 2:
                        rewritten_title = parts[0].strip()
                        rewritten_company = parts[1].strip()
                
                merged_experience.append({
                    "company": rewritten_company,
                    "title": rewritten_title,
                    "start_date": "",
                    "end_date": "",
                    "location": "",
                    "description": "",
                    "bullets": rewritten_exp.get("bullets", []),
                    "is_current": False,
                })
        
        final_resume = {
            "contact": parsed_resume_data.get("contact", {}),
            "summary": rewritten.get("summary") or parsed_resume_data.get("summary", ""),
            "experience": merged_experience,
            "education": parsed_resume_data.get("education", []),
            "skills": rewritten.get("skills", []) or parsed_resume_data.get("skills", []),
            "certifications": parsed_resume_data.get("certifications", []),
            "projects": parsed_resume_data.get("projects", []),
            "languages": parsed_resume_data.get("languages", []),
            "awards": parsed_resume_data.get("awards", []),
        }
    else:
        final_resume = {
            "contact": {},
            "summary": rewritten.get("summary", ""),
            "experience": rewritten.get("experience", []),
            "education": [],
            "skills": rewritten.get("skills", []),
            "certifications": [],
            "projects": [],
            "languages": [],
            "awards": [],
        }
    
    final = tune(final_resume, "general")
    rewritten_text = format_resume_text(final)
    
    # Recalculate ATS score - using advanced scorer
    after_ats = score_detailed_advanced(
        ats_keywords,
        rewritten_text,
        jd_data=result.get("jd_analysis"),
        inferred_skills=None,
        parsed_resume_data=parsed_resume_data,
        enable_semantic=False,
    )
    
    # Recalculate skill gap analysis with approved skills included
    skill_gap_analysis = None
    try:
        from agents.skill_gap_analyzer import analyze_skill_gap
        from agents.skill_inference import infer_skills_from_resume
        
        # Infer skills from the updated resume (which now includes approved skills)
        inferred_skills = infer_skills_from_resume(
            resume_text=rewritten_text,
            explicit_skills=(
                ats_keywords.get("required_skills", [])
                + ats_keywords.get("optional_skills", [])
                + ats_keywords.get("tools", [])
            ),
        )
        
        # Recalculate skill gap - approved skills should no longer be missing
        # Pass explicit skills from final resume to ensure approved skills are checked
        explicit_skills = final.get("skills", [])
        skill_gap_analysis = analyze_skill_gap(
            ats_keywords,
            rewritten_text,
            inferred_skills=inferred_skills,
            explicit_skills=explicit_skills  # Include approved skills explicitly
        )
    except Exception as e:
        logger.warning(f"Failed to recalculate skill gap analysis: {e}")
        # Use existing skill gap analysis if recalculation fails
        skill_gap_analysis = result.get("skill_gap_analysis")
    
    # Update job result - clear approval flags
    updated_result = {
        **result,
        "resume": final,
        "original_resume": original_resume,  # Keep original
        "ats": {
            "before": before_ats,
            "after": after_ats,
        },
        "skill_gap_analysis": skill_gap_analysis,  # Updated skill gap
        "jd_analysis": jd_analysis,
        "parsed_resume_data": parsed_resume_data,
        "approved_skills": approved_skills,
        "pending_skills_approval": [],  # Clear pending skills
        "needs_approval": False,  # Approval completed
    }
    
    update_job(job_id, updated_result)
    
    # Note: We can't directly update RQ job.result because it's a read-only property
    # However, get_job_status() in routes.py checks both RQ and our Redis job tracking
    # Since we've updated Redis via update_job(), the fallback mechanism will work
    # The job_status endpoint prioritizes our Redis storage when RQ result is stale
    
    return {
        "job_id": job_id,
        "status": "completed",
        "result": updated_result,
    }


@router.post("/jobs/{job_id}/calculate-ats")
def calculate_ats_from_text(
    job_id: str,
    edited_text: str = Body(..., embed=True),
):
    """
    Calculate ATS score from edited text without saving changes.
    Allows users to preview ATS score impact before applying changes.
    
    Args:
        job_id: Job ID
        edited_text: The edited resume text to calculate score for
    
    Returns:
        ATS score for the edited text
    """
    from core.job_queue import get_job_status
    from agents.ats_scorer_advanced import score_detailed_advanced_sync
    from agents.resume_parser import parse_resume_async
    import asyncio
    import logging
    
    logger = logging.getLogger(__name__)
    
    # Validate job ID
    try:
        job_id = validate_job_id(job_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Sanitize input
    edited_text = sanitize_resume_text(edited_text)
    
    if not edited_text or len(edited_text.strip()) < 10:
        raise HTTPException(status_code=400, detail="Edited text is too short or empty")
    
    # Get current job result to get JD keywords
    rq_status = get_job_status(job_id)
    job = get_job(job_id)
    
    result = None
    if rq_status and rq_status.get("result"):
        result = rq_status["result"]
    elif job and job.get("result"):
        result = job["result"]
    
    if not result:
        raise HTTPException(status_code=404, detail="Job not found or not completed")
    
    try:
        # Get JD keywords from job result
        jd_analysis = result.get("jd_analysis", {})
        jd_keywords = jd_analysis.get("ats_keywords", {})
        
        if not jd_keywords:
            raise HTTPException(
                status_code=400,
                detail="Job description keywords not found. Cannot calculate ATS score."
            )
        
        # Parse the edited text to get structured data (for better scoring)
        parsed_resume_data = result.get("parsed_resume_data")
        
        # Try to parse edited text (use async in sync context)
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Parse edited text (optional - can use raw text if parsing fails)
        try:
            parsed_edited = loop.run_until_complete(
                parse_resume_async(edited_text, use_cache=False)
            )
        except Exception as e:
            logger.warning(f"Failed to parse edited text, using raw text: {e}")
            parsed_edited = None
        
        # Calculate ATS score using advanced scorer
        ats_result = score_detailed_advanced_sync(
            jd_keywords=jd_keywords,
            resume_text=edited_text,
            jd_data=jd_analysis,
            parsed_resume_data=parsed_edited or parsed_resume_data,
            enable_semantic=False,  # Disable for performance
        )
        
        logger.info(f"Calculated ATS score for edited text: {ats_result.get('score')}")
        
        return {
            "job_id": job_id,
            "score": ats_result.get("score", 0),
            "details": {
                "matched_keywords": ats_result.get("matched_keywords", {}),
                "missing_required": ats_result.get("missing_required", []),
                "coverage": ats_result.get("coverage", {}),
            },
        }
        
    except Exception as e:
        logger.error(f"Failed to calculate ATS score from text: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to calculate ATS score: {str(e)}"
        )


@router.post("/jobs/{job_id}/update-resume")
def update_resume_from_text(
    job_id: str,
    edited_text: str = Body(..., embed=True),
):
    """
    Update resume from edited text.
    Parses the edited text back into structured format and updates the job result.
    
    Args:
        job_id: Job ID
        edited_text: The edited resume text from the user
    
    Returns:
        Updated job result with parsed resume
    """
    from core.job_queue import get_job_status
    from agents.resume_parser import parse_resume_async
    import logging
    
    logger = logging.getLogger(__name__)
    
    # Validate job ID
    try:
        job_id = validate_job_id(job_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Sanitize input
    edited_text = sanitize_resume_text(edited_text)
    
    if not edited_text or len(edited_text.strip()) < 10:
        raise HTTPException(status_code=400, detail="Edited text is too short or empty")
    
    # Get current job result
    rq_status = get_job_status(job_id)
    job = get_job(job_id)
    
    result = None
    if rq_status and rq_status.get("result"):
        result = rq_status["result"]
    elif job and job.get("result"):
        result = job["result"]
    
    if not result:
        raise HTTPException(status_code=404, detail="Job not found or not completed")
    
    try:
        # Parse the edited text back into structured format
        # Use LLM to parse the text back into structured format
        from agents.resume_parser import parse_resume
        import asyncio
        
        # Parse synchronously (using async function in sync context)
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        updated_resume = loop.run_until_complete(
            parse_resume_async(edited_text, use_cache=False)
        )
        
        # Preserve contact info from original if not in edited text
        original_resume = result.get("resume", {})
        if original_resume.get("contact") and not updated_resume.get("contact"):
            updated_resume["contact"] = original_resume["contact"]
        
        # Update job result
        updated_result = {
            **result,
            "resume": updated_resume,
            "edited_by_user": True,  # Flag to indicate user made manual edits
        }
        
        update_job(job_id, updated_result)
        
        logger.info(f"Resume updated from edited text for job {job_id}")
        
        return {
            "job_id": job_id,
            "updated": True,
            "updated_resume": updated_resume,
        }
        
    except Exception as e:
        logger.error(f"Failed to update resume from text: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update resume: {str(e)}"
        )


@router.get("/jobs/{job_id}/download")
def download_tailored_resume(
    job_id: str,
    format: str = "docx",  # docx | pdf | txt | zip
):
    """
    Download the tailored resume from a completed job.
    
    Args:
        job_id: Job ID from /tailor or /tailor/files endpoint
        format: Output format (docx, pdf, txt, or zip)
    
    Returns:
        StreamingResponse with the resume file
    """
    from core.job_queue import get_job_status
    from agents.exporters.txt_exporter import export_txt
    from agents.exporters.zip_exporter import export_zip
    from agents.resume_exporter import export_pdf as export_pdf_stream, export_docx as export_docx_stream
    from agents.templates.pdf_renderer import render_pdf
    from agents.resume_formatter import format_resume_sections
    from fastapi.responses import StreamingResponse, FileResponse
    import tempfile
    
    # Validate job ID format
    try:
        job_id = validate_job_id(job_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Get job status
    rq_status = get_job_status(job_id)
    job = get_job(job_id)
    
    # Get result from either source
    result = None
    if rq_status and rq_status.get("result"):
        result = rq_status["result"]
    elif job and job.get("result"):
        result = job["result"]
    
    if not result:
        raise HTTPException(
            status_code=404,
            detail="Job not found or not completed"
        )
    
    # Check job status
    status = rq_status.get("status") if rq_status else job.get("status")
    if status not in ["completed", "finished"]:
        raise HTTPException(
            status_code=400,
            detail=f"Job is not completed. Current status: {status}"
        )
    
    # Get the tailored resume from result
    tailored_resume = result.get("resume")
    if not tailored_resume:
        raise HTTPException(
            status_code=404,
            detail="Tailored resume not found in job result"
        )
    
    # Validate format
    if format not in ["docx", "pdf", "txt", "zip"]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid format: {format}. Supported: docx, pdf, txt, zip"
        )
    
    # Format resume text for export
    resume_text = format_resume_text(tailored_resume)
    
    # Handle different formats
    if format == "txt":
        return StreamingResponse(
            iter([resume_text]),
            media_type="text/plain",
            headers={
                "Content-Disposition": f'attachment; filename="tailored_resume_{job_id[:8]}.txt"'
            },
        )
    
    if format == "pdf":
        # Try to use template-based PDF rendering if available
        try:
            sections = format_resume_sections(tailored_resume)
            buffer = render_pdf(
                resume_sections=sections,
                template_id="classic",
            )
            return StreamingResponse(
                buffer,
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f'attachment; filename="tailored_resume_{job_id[:8]}.pdf"'
                },
            )
        except Exception:
            # Fallback to simple PDF export
            buffer = export_pdf_stream(resume_text)
            return StreamingResponse(
                buffer,
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f'attachment; filename="tailored_resume_{job_id[:8]}.pdf"'
                },
            )
    
    if format == "zip":
        with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
            zip_path = tmp.name
        
        try:
            export_zip(resume=tailored_resume, zip_path=zip_path)
            return FileResponse(
                zip_path,
                media_type="application/zip",
                filename=f"tailored_resume_{job_id[:8]}.zip",
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create ZIP file: {str(e)}"
            )
    
    # Default: DOCX
    buffer = export_docx_stream(resume_text)
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": f'attachment; filename="tailored_resume_{job_id[:8]}.docx"'
        },
    )


@router.get("/queue/stats")
def get_queue_stats():
    """
    Get job queue statistics.
    
    Returns:
        Queue statistics including queued, processing, completed, and failed jobs
    """
    from core.job_queue import get_queue_stats, get_rq_redis_client
    from rq import Worker
    import logging
    
    logger = logging.getLogger(__name__)
    
    stats = get_queue_stats("default")
    
    # Check if workers are running
    try:
        rq_redis_client = get_rq_redis_client()
        if rq_redis_client:
            # Get active workers
            workers = Worker.all(connection=rq_redis_client)
            stats["active_workers"] = len(workers)
            stats["worker_names"] = [w.name for w in workers] if workers else []
            if stats["active_workers"] == 0:
                stats["worker_warning"] = "No RQ workers are running. Jobs will not be processed. Start worker with: python -m workers.job_worker"
        else:
            stats["active_workers"] = 0
            stats["worker_names"] = []
            stats["worker_warning"] = "Redis connection not available for worker check"
    except Exception as e:
        logger.warning(f"Failed to check worker status: {e}")
        stats["active_workers"] = 0
        stats["worker_names"] = []
        stats["worker_warning"] = f"Could not check workers: {str(e)}"
    
    return stats


@router.post("/ats/compare")
async def compare_ats(
    job_description: str = Form(None),
    jd_file: UploadFile | None = File(None),
    resume: UploadFile = File(...),
):
    """
    Compare ATS scores before and after resume rewrite (async).
    
    Args:
        job_description: Job description text (optional if jd_file provided)
        jd_file: Job description file (optional if job_description provided)
        resume: Resume file (required)
    
    Returns:
        Comparison results with before/after scores and analysis
    """
    from api.files import extract_text_async
    from agents.jd_analyzer import analyze_jd_async
    from agents.resume_rewriter import rewrite_async
    
    # -----------------------------
    # 1️⃣ Input validation
    # -----------------------------
    if not job_description and not jd_file:
        raise HTTPException(
            status_code=400,
            detail="JD text or JD file is required",
        )

    # -----------------------------
    # 2️⃣ Text extraction with file size validation (async)
    # -----------------------------
    try:
        if jd_file:
            jd_text = await extract_text_async(jd_file)
        else:
            # Sanitize text input
            jd_text = sanitize_jd_text(job_description)
        
        resume_text = await extract_text_async(resume)
        
        # Sanitize extracted text
        resume_text = sanitize_resume_text(resume_text)
        if jd_text and not jd_file:
            jd_text = sanitize_jd_text(jd_text)
        
        # Parse resume for structured data (optional, for enhanced ATS scoring)
        parsed_resume_data = None
        try:
            from agents.resume_parser import parse_resume_async
            parsed_resume_data = await parse_resume_async(resume_text, use_cache=True)
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.warning(f"Resume parsing failed (continuing without structured data): {e}")
            parsed_resume_data = None
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
    # 3️⃣ JD analysis (LLM – structured, async)
    # -----------------------------
    jd_data = await analyze_jd_async(jd_text)

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
    # 8️⃣ ATS score BEFORE rewrite (Advanced Scorer)
    # -----------------------------
    before = score_detailed_advanced(
        jd_keywords_all,
        resume_text,
        jd_data=jd_data,
        inferred_skills=inferred_skills,  # ✅ evidence-gated scoring
        parsed_resume_data=parsed_resume_data,  # Use parsed data for better scoring
        enable_semantic=False,  # Disable for performance in API calls
    )

    # -----------------------------
    # 9️⃣ Rewrite resume (LLM – guarded, async)
    # -----------------------------
    try:
        rewritten = await rewrite_async(
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
    # 🔟 ATS score AFTER rewrite (Advanced Scorer)
    # -----------------------------
    after = score_detailed_advanced(
        jd_keywords_all,
        rewritten_text,
        jd_data=jd_data,
        inferred_skills=inferred_skills,
        parsed_resume_data=parsed_resume_data,  # Use same parsed data for consistency
        enable_semantic=False,  # Disable for performance in API calls
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
async def batch_process_jds(
    resume: UploadFile = File(...),
    jd_files: List[UploadFile] = File(...),
    resume_id: str = Form(None),
):
    """
    Process resume against multiple job descriptions at once (async, parallel processing).
    
    Uses parallel processing for 5-10x faster batch operations.
    
    Args:
        resume: Resume file
        jd_files: List of job description files (up to 20)
        resume_id: Optional resume ID for tracking
    
    Returns:
        Batch processing results with scores and recommendations for each JD
    """
    from agents.batch_processor import process_batch_jds_async
    from api.files import extract_text_async
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
    
    # Extract resume text (async)
    try:
        resume_text = await extract_text_async(resume)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to extract resume text: {str(e)}"
        )
    
    # Extract JD texts in parallel (async)
    jd_list = []
    extraction_tasks = []
    
    async def extract_jd_text(jd_file: UploadFile, idx: int) -> Dict[str, str]:
        """Extract text from a single JD file."""
        try:
            jd_text = await extract_text_async(jd_file)
            return {
                "jd_id": jd_file.filename or f"jd_{idx}",
                "jd_text": jd_text,
                "title": jd_file.filename or f"Job {idx + 1}"
            }
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to extract JD {idx}: {e}")
            return {
                "jd_id": f"jd_{idx}",
                "jd_text": "",
                "title": jd_file.filename or f"Job {idx + 1}",
                "error": str(e)
            }
    
    # Extract all JD texts in parallel
    for idx, jd_file in enumerate(jd_files):
        extraction_tasks.append(extract_jd_text(jd_file, idx))
    
    jd_list = await asyncio.gather(*extraction_tasks)
    
    # Process batch (async, parallel JD analysis)
    try:
        results = await process_batch_jds_async(
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
async def batch_process_jds_text(
    resume: UploadFile = File(...),
    jd_texts: List[str] = Form(...),
    jd_titles: Optional[List[str]] = Form(None),
    resume_id: Optional[str] = Form(None),
):
    """
    Process resume against multiple job descriptions (text input, async, parallel processing).
    
    Uses parallel processing for 5-10x faster batch operations.
    
    Args:
        resume: Resume file
        jd_texts: List of job description texts (can be sent as multiple form fields with same name)
        jd_titles: Optional list of job titles
        resume_id: Optional resume ID for tracking
    
    Returns:
        Batch processing results
    """
    from agents.batch_processor import process_batch_jds_async
    from api.files import extract_text_async
    
    # Handle case where jd_texts might be empty or None
    if not jd_texts or len(jd_texts) == 0:
        raise HTTPException(
            status_code=400,
            detail="At least one job description is required"
        )
    
    if len(jd_texts) > 20:
        raise HTTPException(
            status_code=400,
            detail="Maximum 20 job descriptions allowed per batch"
        )
    
    # Extract resume text (async)
    try:
        resume_text = await extract_text_async(resume)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to extract resume text: {str(e)}"
        )
    
    # Prepare JD list with sanitization
    jd_list = []
    titles = jd_titles or []
    
    for idx, jd_text in enumerate(jd_texts):
        try:
            # Sanitize JD text
            sanitized_jd = sanitize_jd_text(jd_text)
            # Sanitize title if provided
            title = sanitize_text(titles[idx], max_length=255) if idx < len(titles) else f"Job {idx + 1}"
            
            jd_list.append({
                "jd_id": f"jd_{idx}",
                "jd_text": sanitized_jd,
                "title": title
            })
        except ValueError as e:
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to sanitize JD {idx}: {e}")
            # Skip invalid JD
            continue
    
    # Process batch (async, parallel JD analysis)
    try:
        results = await process_batch_jds_async(
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


@router.get("/ats/compare/{job_id}")
def get_ats_compare(job_id: str):
    """
    Get ATS comparison (before/after scores) for a completed job.
    
    Args:
        job_id: Job ID from /tailor endpoint
    
    Returns:
        ATS comparison with before/after scores and analysis
    """
    from core.job_queue import get_job_status
    
    # Check both RQ and Redis for job status
    rq_status = get_job_status(job_id)
    job = get_job(job_id)
    
    # Get result from either source
    # Prioritize Redis if it has updated data (from approve_skills)
    result = None
    status = None
    
    # Check if Redis job has updated data (indicated by needs_approval=False and approved_skills)
    if job and job.get("result") and job.get("result", {}).get("needs_approval") is False:
        # This is a recently updated result (from approve_skills), use it
        result = job["result"]
        status = job.get("status")
    elif rq_status and rq_status.get("result"):
        result = rq_status["result"]
        status = rq_status.get("status")
    elif job and job.get("result"):
        result = job["result"]
        status = job.get("status")
    
    if not result:
        raise HTTPException(
            status_code=404,
            detail="Job not found or not completed"
        )
    
    # Check if job failed
    if status == "failed" or (rq_status and rq_status.get("error")) or (job and job.get("error")):
        error_msg = (rq_status and rq_status.get("error")) or (job and job.get("error")) or "Unknown error"
        raise HTTPException(
            status_code=400,
            detail=f"Job failed: {error_msg}"
        )
    
    # Check if job is completed (handle both "completed" and "finished" statuses)
    if status not in ["completed", "finished"]:
        raise HTTPException(
            status_code=404,
            detail=f"Job not completed. Current status: {status or 'unknown'}"
        )
    
    # Extract ATS comparison data from job result
    ats_data = result.get("ats", {})
    if not ats_data:
        raise HTTPException(
            status_code=404,
            detail="ATS comparison data not available for this job"
        )
    
    # Format response similar to /ats/compare POST endpoint
    before_ats = ats_data.get("before", {})
    after_ats = ats_data.get("after", {})
    
    return {
        "before": {
            "score": before_ats.get("score", 0),
            "keywords_matched": len(before_ats.get("matched_keywords", {}).get("required_skills", [])) + 
                              len(before_ats.get("matched_keywords", {}).get("tools", [])) +
                              len(before_ats.get("matched_keywords", {}).get("optional_skills", [])),
            "missing_keywords": before_ats.get("missing_required", []),
        },
        "after": {
            "score": after_ats.get("score", 0),
            "keywords_matched": len(after_ats.get("matched_keywords", {}).get("required_skills", [])) + 
                              len(after_ats.get("matched_keywords", {}).get("tools", [])) +
                              len(after_ats.get("matched_keywords", {}).get("optional_skills", [])),
            "missing_keywords": after_ats.get("missing_required", []),
        },
    }


@router.get("/ats/compare/{job_id}/skill-gap")
def get_skill_gap_analysis(job_id: str):
    """
    Get skill gap analysis for a completed job.
    
    Args:
        job_id: Job ID from /ats/compare endpoint
    
    Returns:
        Skill gap analysis with missing skills and recommendations
    """
    from core.job_queue import get_job_status
    
    # Check both RQ and Redis for job status
    rq_status = get_job_status(job_id)
    job = get_job(job_id)
    
    # Get result from either source
    # Prioritize Redis if it has updated data (from approve_skills)
    result = None
    status = None
    
    # Check if Redis job has updated data (indicated by needs_approval=False and approved_skills)
    if job and job.get("result") and job.get("result", {}).get("needs_approval") is False:
        # This is a recently updated result (from approve_skills), use it
        result = job["result"]
        status = job.get("status")
    elif rq_status and rq_status.get("result"):
        result = rq_status["result"]
        status = rq_status.get("status")
    elif job and job.get("result"):
        result = job["result"]
        status = job.get("status")
    
    if not result:
        raise HTTPException(
            status_code=404,
            detail="Job not found or not completed"
        )
    
    # Check if job failed
    if status == "failed" or (rq_status and rq_status.get("error")) or (job and job.get("error")):
        error_msg = (rq_status and rq_status.get("error")) or (job and job.get("error")) or "Unknown error"
        raise HTTPException(
            status_code=400,
            detail=f"Job failed: {error_msg}"
        )
    
    # Check if job is completed (handle both "completed" and "finished" statuses)
    if status not in ["completed", "finished"]:
        raise HTTPException(
            status_code=404,
            detail=f"Job not completed. Current status: {status or 'unknown'}"
        )
    
    if "skill_gap_analysis" in result:
        skill_gap = result["skill_gap_analysis"]
        
        # Map backend format to frontend expected format
        # Frontend expects: skill_match_percentage, missing_skills (flat array), recommended_skills
        summary = skill_gap.get("summary", {})
        required_coverage = summary.get("required_coverage", 0)
        optional_coverage = summary.get("optional_coverage", 0)
        tools_coverage = summary.get("tools_coverage", 0)
        
        # Calculate overall skill match percentage (weighted average)
        total_required = summary.get("total_required", 0)
        total_optional = summary.get("total_optional", 0)
        total_tools = summary.get("total_tools", 0)
        total_skills = total_required + total_optional + total_tools
        
        if total_skills > 0:
            # Calculate weighted average of coverage percentages
            # Weight: required (50%), optional (30%), tools (20%)
            # Formula: weighted average of coverage percentages
            total_weight = (total_required * 0.5) + (total_optional * 0.3) + (total_tools * 0.2)
            if total_weight > 0:
                skill_match_percentage = (
                    (required_coverage * total_required * 0.5) +
                    (optional_coverage * total_optional * 0.3) +
                    (tools_coverage * total_tools * 0.2)
                ) / total_weight
            else:
                skill_match_percentage = 0
            # Cap at 100% (shouldn't exceed, but safety check)
            skill_match_percentage = min(skill_match_percentage, 100.0)
        else:
            skill_match_percentage = 0
        
        # Flatten missing skills and deduplicate
        missing_skills_flat = []
        missing_skills_dict = skill_gap.get("missing_skills", {})
        missing_skills_flat.extend(missing_skills_dict.get("required_skills", []))
        missing_skills_flat.extend(missing_skills_dict.get("optional_skills", []))
        missing_skills_flat.extend(missing_skills_dict.get("tools", []))
        
        # Deduplicate and normalize similar skills, preferring JD terminology
        from agents.skill_normalizer import deduplicate_skills
        # Get JD skills from the job result if available
        jd_analysis = result.get("jd_analysis", {})
        jd_keywords = jd_analysis.get("ats_keywords", {}) if isinstance(jd_analysis, dict) else {}
        all_jd_skills = []
        if isinstance(jd_keywords, dict):
            all_jd_skills.extend(jd_keywords.get("required_skills", []))
            all_jd_skills.extend(jd_keywords.get("optional_skills", []))
            all_jd_skills.extend(jd_keywords.get("tools", []))
        elif isinstance(jd_keywords, list):
            all_jd_skills = jd_keywords
        
        missing_skills_flat = deduplicate_skills(
            missing_skills_flat,
            preferred_skills=all_jd_skills
        )
        
        # Extract recommended skills from recommendations
        recommended_skills = []
        recommendations = skill_gap.get("recommendations", [])
        for rec in recommendations:
            if isinstance(rec, dict) and "skill" in rec:
                recommended_skills.append(rec["skill"])
            elif isinstance(rec, str):
                recommended_skills.append(rec)
        
        # Return mapped format
        return {
            "skill_match_percentage": round(skill_match_percentage, 1),
            "missing_skills": missing_skills_flat,
            "recommended_skills": recommended_skills,
            # Also include original data for detailed views
            "summary": summary,
            "present_skills": skill_gap.get("present_skills", {}),
            "missing_skills_by_category": missing_skills_dict,
            "gap_severity": skill_gap.get("gap_severity", "unknown"),
        }
    
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
    
    # Sanitize inputs
    try:
        title = sanitize_text(title, max_length=255)
        user_id = validate_user_id(user_id)
        tag_list = validate_tags(tags) if tags else []
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
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
        # Validate file security first (size, content-type, virus scan)
        from api.files import extract_text
        from core.security import sanitize_filename
        
        # Sanitize filename
        try:
            safe_filename = sanitize_filename(resume_file.filename)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid filename: {str(e)}")
        
        # Extract text (this performs full security validation)
        # We don't need the text, but this validates the file
        try:
            extract_text(resume_file)
            # Reset file pointer for format validation
            resume_file.file.seek(0)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        
        # Save file temporarily for format validation
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
    """
    List all available resume templates.
    
    Returns:
        List of templates with metadata (id, name, description, ats_friendly, best_for, etc.)
    """
    from agents.templates.registry import list_templates as get_templates_list
    return get_templates_list()


@router.get("/ats/templates/{template_id}")
def get_template_details(template_id: str):
    """
    Get detailed information about a specific template.
    
    Args:
        template_id: Template ID
    
    Returns:
        Full template configuration and metadata
    """
    from agents.templates.registry import get_template_details
    
    template = get_template_details(template_id)
    if not template:
        raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found")
    
    return template


@router.post("/ats/templates/customize")
def customize_template(
    base_template_id: str = Form(...),
    font: str = Form(None),
    heading_size: int = Form(None),
    body_size: int = Form(None),
    line_spacing: int = Form(None),
    section_spacing: int = Form(None),
    accent: bool = Form(None),
    color_scheme: str = Form(None),
):
    """
    Create a customized template based on an existing template.
    
    Args:
        base_template_id: ID of base template to customize
        font: Custom font name (optional)
        heading_size: Custom heading size (optional, 8-24)
        body_size: Custom body size (optional, 8-14)
        line_spacing: Custom line spacing (optional, 4-20)
        section_spacing: Custom section spacing (optional, 8-30)
        accent: Enable/disable accent colors (optional)
        color_scheme: Color scheme (optional: monochrome, blue, green, professional)
    
    Returns:
        Custom template configuration
    """
    from agents.templates.registry import create_custom_template, validate_template_config
    
    # Build customizations dict
    customizations = {}
    if font:
        customizations["font"] = sanitize_text(font, max_length=50)
    if heading_size is not None:
        customizations["heading_size"] = heading_size
    if body_size is not None:
        customizations["body_size"] = body_size
    if line_spacing is not None:
        customizations["line_spacing"] = line_spacing
    if section_spacing is not None:
        customizations["section_spacing"] = section_spacing
    if accent is not None:
        customizations["accent"] = accent
    if color_scheme:
        allowed_schemes = ["monochrome", "blue", "green", "professional"]
        if color_scheme not in allowed_schemes:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid color_scheme. Allowed: {', '.join(allowed_schemes)}"
            )
        customizations["color_scheme"] = color_scheme
    
    try:
        custom_template = create_custom_template(base_template_id, customizations)
        return {
            "base_template": base_template_id,
            "custom_template": custom_template,
            "customizations": customizations,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/ats/templates/preview")
def preview_template(
    rewritten_resume: dict,
    template_id: str = Form("classic"),
    custom_template: dict = Form(None),
):
    """
    Preview a resume with a specific template without downloading.
    
    Args:
        rewritten_resume: Rewritten resume data
        template_id: Template ID to preview
        custom_template: Optional custom template configuration
    
    Returns:
        Template preview information (metadata, not actual PDF)
    """
    from agents.resume_formatter import format_resume_sections
    from agents.templates.registry import get_template
    
    # Validate template
    if custom_template:
        from agents.templates.registry import validate_template_config
        is_valid, error = validate_template_config(custom_template)
        if not is_valid:
            raise HTTPException(status_code=400, detail=f"Invalid custom template: {error}")
        template = custom_template
    else:
        template = get_template(template_id)
        if not template:
            raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found")
    
    # Format resume sections
    sections = format_resume_sections(rewritten_resume)
    
    # Calculate estimated page count (rough estimate)
    estimated_pages = _estimate_page_count(sections, template)
    
    return {
        "template_id": template_id if not custom_template else "custom",
        "template_name": template["name"],
        "estimated_pages": estimated_pages,
        "sections_included": list(sections.keys()),
        "template_config": {
            "font": template["font"],
            "heading_size": template["heading_size"],
            "body_size": template["body_size"],
            "color_scheme": template.get("color_scheme", "monochrome"),
            "layout": template.get("layout", "single-column"),
        },
    }


def _estimate_page_count(sections: dict, template: dict) -> int:
    """Estimate number of pages for the resume."""
    # Rough estimation based on content length
    total_chars = 0
    
    if sections.get("summary"):
        total_chars += len(sections["summary"])
    
    for exp in sections.get("experience", []):
        total_chars += len(exp.get("title", ""))
        for bullet in exp.get("bullets", []):
            total_chars += len(bullet)
    
    total_chars += len(", ".join(sections.get("skills", [])))
    
    # Rough estimate: ~2000 characters per page for typical resume
    pages = max(1, int(total_chars / 2000))
    return pages


@router.post("/ats/download/pdf")
def download_pdf(
    rewritten_resume: dict,
    template_id: str = Form("classic"),
    custom_template: dict = Form(None),
):
    """
    Download resume as PDF with specified template.
    
    Args:
        rewritten_resume: Rewritten resume data
        template_id: Template ID (default: "classic")
        custom_template: Optional custom template configuration (overrides template_id)
    
    Returns:
        PDF file download
    """
    sections = format_resume_sections(rewritten_resume)

    buffer = render_pdf(
        resume_sections=sections,
        template_id=template_id,
        custom_template=custom_template,
    )

    template_name = custom_template.get("name", template_id) if custom_template else template_id
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f"attachment; filename=resume_{template_name}.pdf"
            )
        },
    )


@router.post("/ats/download/zip")
def download_zip(
    rewritten_resume: dict,
    template_id: str = "classic",
):
    """
    Download a ZIP bundle containing DOCX, PDF, and TXT versions.
    """
    import tempfile
    from fastapi.responses import FileResponse
    from agents.exporters.zip_exporter import export_zip

    # Create a temporary zip file, export content, then stream it back
    with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
        zip_path = tmp.name

    try:
        export_zip(resume=rewritten_resume, zip_path=zip_path)
        return FileResponse(
            zip_path,
            media_type="application/zip",
            filename="resume_bundle.zip",
        )
    finally:
        # Cleanup handled by FileResponse after streaming; if needed, the OS will reclaim
        pass

# ============================================================
# Resume Versioning UI Endpoints
# ============================================================

@router.get("/resumes/{resume_id}/versions")
async def list_resume_versions(resume_id: str):
    """
    List all versions for a resume.
    
    Args:
        resume_id: Resume ID
    
    Returns:
        List of versions with metadata
    """
    from db.repositories import get_resume_versions
    from db.database import SessionLocal
    from core.security import validate_user_id
    
    # Validate resume_id format (UUID)
    try:
        from uuid import UUID
        resume_uuid = UUID(resume_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid resume ID format")
    
    try:
        async with SessionLocal() as session:
            versions = await get_resume_versions(session, resume_uuid, limit=100)
            
            return [
                {
                    "version_id": str(v.id),
                    "version_number": v.version_number,
                    "created_at": v.created_at.isoformat(),
                    "change_summary": v.change_summary,
                    "parent_version_id": str(v.parent_version_id) if v.parent_version_id else None,
                }
                for v in versions
            ]
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to list versions: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve versions: {str(e)}"
        )


@router.get("/resumes/{resume_id}/versions/{version_id}")
async def get_resume_version(resume_id: str, version_id: str):
    """
    Get a specific resume version.
    
    Args:
        resume_id: Resume ID
        version_id: Version ID
    
    Returns:
        Version data with resume content
    """
    from db.repositories import get_resume_version_by_id
    from db.database import SessionLocal
    from uuid import UUID
    
    try:
        resume_uuid = UUID(resume_id)
        version_uuid = UUID(version_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID format")
    
    try:
        async with SessionLocal() as session:
            version = await get_resume_version_by_id(session, version_uuid)
            
            if not version:
                raise HTTPException(status_code=404, detail="Version not found")
            
            # Verify version belongs to resume
            if version.resume_id != resume_uuid:
                raise HTTPException(status_code=404, detail="Version not found for this resume")
            
            return {
                "version_id": str(version.id),
                "version_number": version.version_number,
                "resume_id": str(version.resume_id),
                "created_at": version.created_at.isoformat(),
                "change_summary": version.change_summary,
                "parent_version_id": str(version.parent_version_id) if version.parent_version_id else None,
                "resume_data": version.resume_data,
            }
    except HTTPException:
        raise
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to get version: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve version: {str(e)}"
        )


@router.get("/resumes/{resume_id}/versions/{version_id}/compare")
async def compare_resume_versions(
    resume_id: str,
    version_id: str,
    compare_with: Optional[str] = None,
):
    """
    Compare two resume versions with visual diff and side-by-side comparison.
    
    Args:
        resume_id: Resume ID
        version_id: First version ID to compare
        compare_with: Second version ID (optional, defaults to current version)
    
    Returns:
        Visual diff with structured comparison and side-by-side format
    """
    from db.repositories import get_resume_version_by_id, get_resume_by_id
    from db.database import SessionLocal
    from agents.diff_viewer import diff_resume_structured
    from uuid import UUID
    
    try:
        resume_uuid = UUID(resume_id)
        version1_uuid = UUID(version_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID format")
    
    try:
        async with SessionLocal() as session:
            # Get version 1
            version1 = await get_resume_version_by_id(session, version1_uuid)
            if not version1 or version1.resume_id != resume_uuid:
                raise HTTPException(status_code=404, detail="Version 1 not found")
            
            # Get version 2 (or current resume)
            if compare_with:
                try:
                    version2_uuid = UUID(compare_with)
                    version2 = await get_resume_version_by_id(session, version2_uuid)
                    if not version2 or version2.resume_id != resume_uuid:
                        raise HTTPException(status_code=404, detail="Version 2 not found")
                    version2_data = version2.resume_data
                    version2_meta = {
                        "version_id": str(version2.id),
                        "version_number": version2.version_number,
                        "created_at": version2.created_at.isoformat(),
                        "change_summary": version2.change_summary,
                    }
                except ValueError:
                    raise HTTPException(status_code=400, detail="Invalid compare_with ID format")
            else:
                # Compare with current resume
                resume = await get_resume_by_id(session, resume_uuid)
                if not resume:
                    raise HTTPException(status_code=404, detail="Resume not found")
                version2_data = resume.resume_data or {}
                version2_meta = {
                    "version_id": "current",
                    "version_number": resume.version_count,
                    "created_at": resume.updated_at.isoformat(),
                    "change_summary": "Current version",
                }
            
            # Extract resume data
            version1_data = version1.resume_data or {}
            
            # Generate visual diff
            visual_diff = diff_resume_structured(
                version1_data,
                version2_data,
                include_side_by_side=True
            )
            
            return {
                "version1": {
                    "version_id": str(version1.id),
                    "version_number": version1.version_number,
                    "created_at": version1.created_at.isoformat(),
                    "change_summary": version1.change_summary,
                },
                "version2": version2_meta,
                **visual_diff,  # Includes comparison, statistics, side_by_side
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to compare versions: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to compare versions: {str(e)}"
        )


# ============================================================
# API Analytics Endpoints
# ============================================================

@router.get("/analytics/usage")
async def get_api_usage_analytics(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    endpoint: Optional[str] = None,
    limit: int = 50,
):
    """
    Get API usage analytics.
    
    Args:
        start_date: Start date in ISO format (e.g., "2024-01-01T00:00:00")
        end_date: End date in ISO format (e.g., "2024-01-31T23:59:59")
        endpoint: Filter by specific endpoint (optional)
        limit: Maximum number of results (default: 50)
    
    Returns:
        Aggregated API usage statistics by endpoint
    """
    from db.repositories import get_api_usage_stats
    from db.database import SessionLocal
    from datetime import datetime
    
    try:
        # Parse dates if provided
        start_dt = None
        end_dt = None
        
        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid start_date format. Use ISO format.")
        
        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid end_date format. Use ISO format.")
        
        async with SessionLocal() as session:
            stats = await get_api_usage_stats(
                session=session,
                start_date=start_dt,
                end_date=end_dt,
                endpoint=endpoint,
                limit=limit,
            )
            
            return {
                "period": {
                    "start_date": start_date,
                    "end_date": end_date,
                },
                "total_endpoints": len(stats),
                "endpoints": stats,
            }
    except HTTPException:
        raise
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to get API usage analytics: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve analytics: {str(e)}"
        )


@router.get("/analytics/usage/top")
async def get_top_endpoints(
    limit: int = 10,
    days: int = 7,
):
    """
    Get top N most used endpoints.
    
    Args:
        limit: Number of top endpoints to return (default: 10)
        days: Number of days to look back (default: 7)
    
    Returns:
        Top endpoints by request count
    """
    from db.repositories import get_top_endpoints
    from db.database import SessionLocal
    from datetime import datetime, timedelta
    
    try:
        start_date = datetime.utcnow() - timedelta(days=days)
        
        async with SessionLocal() as session:
            top_endpoints = await get_top_endpoints(
                session=session,
                limit=limit,
                start_date=start_date,
            )
            
            return {
                "period_days": days,
                "total_endpoints": len(top_endpoints),
                "top_endpoints": top_endpoints,
            }
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to get top endpoints: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve top endpoints: {str(e)}"
        )


@router.get("/analytics/usage/endpoint/{endpoint_path:path}")
async def get_endpoint_usage(
    endpoint_path: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 100,
):
    """
    Get detailed usage statistics for a specific endpoint.
    
    Args:
        endpoint_path: Endpoint path (e.g., "/tailor", "/ats/compare")
        start_date: Start date in ISO format
        end_date: End date in ISO format
        limit: Maximum number of records to return
    
    Returns:
        Detailed usage records for the endpoint
    """
    from db.repositories import get_api_usage_by_endpoint
    from db.database import SessionLocal
    from datetime import datetime
    
    try:
        # Parse dates if provided
        start_dt = None
        end_dt = None
        
        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid start_date format.")
        
        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid end_date format.")
        
        # Ensure endpoint starts with /
        if not endpoint_path.startswith("/"):
            endpoint_path = "/" + endpoint_path
        
        async with SessionLocal() as session:
            usage_records = await get_api_usage_by_endpoint(
                session=session,
                endpoint=endpoint_path,
                start_date=start_dt,
                end_date=end_dt,
                limit=limit,
            )
            
            return {
                "endpoint": endpoint_path,
                "period": {
                    "start_date": start_date,
                    "end_date": end_date,
                },
                "total_records": len(usage_records),
                "records": [
                    {
                        "id": str(record.id),
                        "method": record.method,
                        "status_code": record.status_code,
                        "response_time_ms": record.response_time_ms,
                        "client_ip": record.client_ip,
                        "created_at": record.created_at.isoformat(),
                        "error_message": record.error_message,
                    }
                    for record in usage_records
                ],
            }
    except HTTPException:
        raise
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to get endpoint usage: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve endpoint usage: {str(e)}"
        )


@router.get("/analytics/usage/summary")
async def get_usage_summary(
    days: int = 7,
):
    """
    Get overall usage summary.
    
    Args:
        days: Number of days to look back (default: 7)
    
    Returns:
        Summary statistics including total requests, top endpoints, error rates, etc.
    """
    from db.repositories import get_api_usage_stats
    from db.database import SessionLocal
    from datetime import datetime, timedelta
    from sqlalchemy import func, select
    
    try:
        start_date = datetime.utcnow() - timedelta(days=days)
        
        async with SessionLocal() as session:
            # Get aggregated stats
            stats = await get_api_usage_stats(
                session=session,
                start_date=start_date,
                limit=100,
            )
            
            # Calculate totals
            total_requests = sum(s["total_requests"] for s in stats)
            total_errors = sum(s["error_count"] for s in stats)
            total_success = sum(s["success_count"] for s in stats)
            
            # Get top 5 endpoints
            top_endpoints = sorted(stats, key=lambda x: x["total_requests"], reverse=True)[:5]
            
            # Calculate average response time across all endpoints
            avg_response_times = [s["avg_response_time_ms"] for s in stats if s["avg_response_time_ms"]]
            overall_avg_response_time = sum(avg_response_times) / len(avg_response_times) if avg_response_times else None
            
            return {
                "period_days": days,
                "summary": {
                    "total_requests": total_requests,
                    "total_success": total_success,
                    "total_errors": total_errors,
                    "error_rate": total_errors / total_requests if total_requests > 0 else 0,
                    "success_rate": total_success / total_requests if total_requests > 0 else 0,
                    "overall_avg_response_time_ms": overall_avg_response_time,
                },
                "top_endpoints": top_endpoints,
                "total_unique_endpoints": len(stats),
            }
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to get usage summary: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve usage summary: {str(e)}"
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
