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
from agents.keyword_confidence import keyword_confidence
from agents.resume_risk import resume_risk_flags
from agents.jd_fit import classify_jd_fit
from agents.skill_inference import infer_skills_from_resume
from agents.role_confidence import tune_confidence_by_role
from agents.role_detector import detect_role
from agents.role_rules import ROLE_CONFIDENCE_THRESHOLDS
from agents.rewrite_validator import validate_rewrite
from agents.jd_normalizer import normalize_jd_keywords
from fastapi.responses import StreamingResponse
from agents.resume_formatter import format_resume_text
from agents.resume_exporter import export_docx
from agents.templates.registry import TEMPLATES
from fastapi.responses import StreamingResponse
from agents.resume_formatter import format_resume_sections
from agents.templates.pdf_renderer import render_pdf
from fastapi.responses import StreamingResponse
from agents.exporters.zip_exporter import export_zip
from agents.templates.recommender import recommend_templates
from agents.templates.registry import TEMPLATES
from fastapi.responses import FileResponse
from agents.exporters.pdf_exporter import export_pdf
from agents.exporters.docx_exporter import export_docx
from agents.exporters.txt_exporter import export_txt
from agents.exporters.zip_exporter import export_zip
import tempfile




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
@router.post("/ats/compare")
def compare_ats(
    job_description: str = Form(None),
    jd_file: UploadFile | None = File(None),
    resume: UploadFile = File(...),
):
    # -----------------------------
    # 1️⃣ Input validation
    # -----------------------------
    if not job_description and not jd_file:
        raise HTTPException(
            status_code=400,
            detail="JD text or JD file is required",
        )

    # -----------------------------
    # 2️⃣ Text extraction
    # -----------------------------
    jd_text = extract_text(jd_file) if jd_file else job_description
    resume_text = extract_text(resume)

    if not jd_text.strip() or not resume_text.strip():
        raise HTTPException(
            status_code=400,
            detail="Failed to extract text from JD or resume",
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
    rewritten = rewrite(
        safe_keywords,
        resume_text,
    )

    # 🔒 POST-LLM SELF-CHECK (ANTI-HALLUCINATION)
    rewritten = validate_rewrite(
        rewritten,
        resume_text,
        safe_keywords,
    )

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
    }

@router.post("/ats/download")
def download_resume(
    rewritten_resume: dict,
    format: str = "docx",  # docx | txt | pdf
):
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
        buffer = export_pdf(resume_text)
        return StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers={
                "Content-Disposition": "attachment; filename=resume.pdf"
            },
        )

    # default → DOCX
    buffer = export_docx(resume_text)
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
    ids = recommend_templates(role_info)

    return [
        {
            "id": t,
            "name": TEMPLATES[t]["name"],
        }
        for t in ids
    ]


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
        export_pdf(resume, tmp.name)
        return FileResponse(tmp.name, filename="resume.pdf")

    if format == "docx":
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
