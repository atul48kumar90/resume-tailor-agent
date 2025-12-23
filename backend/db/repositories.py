# db/repositories.py
"""
Repository pattern for database operations.
Provides clean abstraction for database access.
"""
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_, or_
from sqlalchemy.orm import selectinload

from db.models import (
    User, Resume, ResumeVersion, JobDescription, Application, Job, APIUsage
)

logger = logging.getLogger(__name__)


# ============================================================
# User Repository
# ============================================================

async def get_or_create_user(
    session: AsyncSession,
    email: str,
    username: Optional[str] = None
) -> User:
    """Get existing user or create new one."""
    stmt = select(User).where(User.email == email)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        user = User(email=email, username=username)
        session.add(user)
        await session.flush()
        logger.info(f"Created new user: {user.id}")
    
    return user


async def get_user_by_id(session: AsyncSession, user_id: UUID) -> Optional[User]:
    """Get user by ID."""
    stmt = select(User).where(User.id == user_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


# ============================================================
# Resume Repository
# ============================================================

async def create_resume(
    session: AsyncSession,
    user_id: UUID,
    title: str,
    resume_data: Optional[Dict[str, Any]] = None,
    resume_text: Optional[str] = None,
    tags: Optional[List[str]] = None,
    parsed_resume_data: Optional[Dict[str, Any]] = None,
) -> Resume:
    """
    Create a new resume.
    
    Args:
        session: Database session
        user_id: User ID
        title: Resume title
        resume_data: Structured resume data (legacy format)
        resume_text: Plain text resume
        tags: Tags for categorization
        parsed_resume_data: Parsed structured data from resume_parser
    
    Returns:
        Created Resume object
    """
    # If parsed_resume_data is provided, merge it with resume_data
    if parsed_resume_data:
        if resume_data:
            # Merge parsed data into existing resume_data
            resume_data.update(parsed_resume_data)
        else:
            # Use parsed data as resume_data
            resume_data = parsed_resume_data
    
    resume = Resume(
        user_id=user_id,
        title=title,
        resume_data=resume_data,
        resume_text=resume_text,
        tags=tags or [],
        version_count=1,
        application_count=0,
    )
    session.add(resume)
    await session.flush()
    logger.info(f"Created resume: {resume.id} with structured data")
    return resume


async def get_resume_by_id(
    session: AsyncSession,
    resume_id: UUID,
    include_versions: bool = False
) -> Optional[Resume]:
    """Get resume by ID."""
    stmt = select(Resume).where(Resume.id == resume_id)
    
    if include_versions:
        stmt = stmt.options(selectinload(Resume.versions))
    
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_user_resumes(
    session: AsyncSession,
    user_id: UUID,
    limit: int = 100,
    offset: int = 0
) -> List[Resume]:
    """Get all resumes for a user."""
    stmt = (
        select(Resume)
        .where(Resume.user_id == user_id)
        .order_by(Resume.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def update_resume_stats(
    session: AsyncSession,
    resume_id: UUID,
    **kwargs
) -> Optional[Resume]:
    """Update resume statistics."""
    resume = await get_resume_by_id(session, resume_id)
    if not resume:
        return None
    
    for key, value in kwargs.items():
        if hasattr(resume, key):
            setattr(resume, key, value)
    
    resume.updated_at = datetime.utcnow()
    await session.flush()
    return resume


# ============================================================
# Resume Version Repository
# ============================================================

async def create_resume_version(
    session: AsyncSession,
    resume_id: UUID,
    resume_data: Dict[str, Any],
    change_summary: Optional[str] = None,
    parent_version_id: Optional[UUID] = None
) -> ResumeVersion:
    """Create a new resume version."""
    # Get current version count
    stmt = select(func.max(ResumeVersion.version_number)).where(
        ResumeVersion.resume_id == resume_id
    )
    result = await session.execute(stmt)
    max_version = result.scalar() or 0
    
    version = ResumeVersion(
        resume_id=resume_id,
        parent_version_id=parent_version_id,
        version_number=max_version + 1,
        resume_data=resume_data,
        change_summary=change_summary,
    )
    session.add(version)
    
    # Update resume version count
    await update_resume_stats(session, resume_id, version_count=max_version + 1)
    
    await session.flush()
    logger.info(f"Created resume version: {version.id}")
    return version


async def get_resume_version_by_id(
    session: AsyncSession,
    version_id: UUID
) -> Optional[ResumeVersion]:
    """Get resume version by ID."""
    stmt = select(ResumeVersion).where(ResumeVersion.id == version_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_resume_versions(
    session: AsyncSession,
    resume_id: UUID,
    limit: int = 50
) -> List[ResumeVersion]:
    """Get all versions for a resume."""
    stmt = (
        select(ResumeVersion)
        .where(ResumeVersion.resume_id == resume_id)
        .order_by(ResumeVersion.version_number.desc())
        .limit(limit)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_current_version(
    session: AsyncSession,
    resume_id: UUID
) -> Optional[ResumeVersion]:
    """Get the current (latest) version of a resume."""
    stmt = (
        select(ResumeVersion)
        .where(ResumeVersion.resume_id == resume_id)
        .order_by(ResumeVersion.version_number.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


# ============================================================
# Job Description Repository
# ============================================================

async def create_job_description(
    session: AsyncSession,
    title: str,
    jd_text: str,
    user_id: Optional[UUID] = None,
    company: Optional[str] = None,
    analyzed_data: Optional[Dict[str, Any]] = None
) -> JobDescription:
    """Create a new job description."""
    jd = JobDescription(
        user_id=user_id,
        title=title,
        company=company,
        jd_text=jd_text,
        role=analyzed_data.get("role") if analyzed_data else None,
        seniority=analyzed_data.get("seniority") if analyzed_data else None,
        required_skills=analyzed_data.get("required_skills", []) if analyzed_data else [],
        optional_skills=analyzed_data.get("optional_skills", []) if analyzed_data else [],
        tools=analyzed_data.get("tools", []) if analyzed_data else [],
        responsibilities=analyzed_data.get("responsibilities", []) if analyzed_data else [],
        ats_keywords=analyzed_data.get("ats_keywords", []) if analyzed_data else [],
    )
    session.add(jd)
    await session.flush()
    logger.info(f"Created job description: {jd.id}")
    return jd


# ============================================================
# Application Repository
# ============================================================

async def create_application(
    session: AsyncSession,
    resume_id: UUID,
    user_id: UUID,
    job_title: str,
    ats_score: Optional[float] = None,
    fit_score: Optional[float] = None,
    job_description_id: Optional[UUID] = None,
    company: Optional[str] = None,
    status: str = "applied",
    skill_gap_details: Optional[Dict[str, Any]] = None,
    recommendations: Optional[List[str]] = None
) -> Application:
    """Create a new application."""
    application = Application(
        resume_id=resume_id,
        user_id=user_id,
        job_description_id=job_description_id,
        job_title=job_title,
        company=company,
        status=status,
        ats_score=ats_score,
        fit_score=fit_score,
        skill_gap_severity=skill_gap_details.get("gap_severity") if skill_gap_details else None,
        required_coverage=skill_gap_details.get("summary", {}).get("required_coverage") if skill_gap_details else None,
        missing_required_count=len(skill_gap_details.get("missing_skills", {}).get("required_skills", [])) if skill_gap_details else None,
        skill_gap_details=skill_gap_details,
        recommendations=recommendations,
    )
    session.add(application)
    
    # Update resume application count
    resume = await get_resume_by_id(session, resume_id)
    if resume:
        resume.application_count += 1
        resume.total_applications += 1
        if ats_score:
            # Update average ATS score
            total_score = resume.average_ats_score * (resume.total_applications - 1) + ats_score
            resume.average_ats_score = total_score / resume.total_applications
    
    await session.flush()
    logger.info(f"Created application: {application.id}")
    return application


async def get_user_applications(
    session: AsyncSession,
    user_id: UUID,
    limit: int = 100,
    offset: int = 0
) -> List[Application]:
    """Get all applications for a user."""
    stmt = (
        select(Application)
        .where(Application.user_id == user_id)
        .order_by(Application.application_date.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_resume_applications(
    session: AsyncSession,
    resume_id: UUID
) -> List[Application]:
    """Get all applications for a resume."""
    stmt = (
        select(Application)
        .where(Application.resume_id == resume_id)
        .order_by(Application.application_date.desc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


# ============================================================
# Job Repository (for background jobs)
# ============================================================

async def create_job(
    session: AsyncSession,
    rq_job_id: Optional[str] = None
) -> Job:
    """Create a new background job."""
    job = Job(
        rq_job_id=rq_job_id,
        status="pending"
    )
    session.add(job)
    await session.flush()
    logger.info(f"Created job: {job.id}")
    return job


async def get_job_by_id(session: AsyncSession, job_id: UUID) -> Optional[Job]:
    """Get job by ID."""
    stmt = select(Job).where(Job.id == job_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def update_job(
    session: AsyncSession,
    job_id: UUID,
    status: Optional[str] = None,
    result: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None,
    started_at: Optional[datetime] = None,
    completed_at: Optional[datetime] = None
) -> Optional[Job]:
    """Update job status."""
    job = await get_job_by_id(session, job_id)
    if not job:
        return None
    
    if status:
        job.status = status
    if result is not None:
        job.result = result
    if error:
        job.error = error
    if started_at:
        job.started_at = started_at
    if completed_at:
        job.completed_at = completed_at
    
    await session.flush()
    return job


# ============================================================
# API Usage Repository
# ============================================================

async def create_api_usage(
    session: AsyncSession,
    endpoint: str,
    method: str,
    status_code: int,
    user_id: Optional[UUID] = None,
    client_ip: Optional[str] = None,
    response_time_ms: Optional[int] = None,
    request_size_bytes: Optional[int] = None,
    response_size_bytes: Optional[int] = None,
    user_agent: Optional[str] = None,
    error_message: Optional[str] = None,
) -> APIUsage:
    """Create a new API usage record."""
    usage = APIUsage(
        endpoint=endpoint,
        method=method,
        user_id=user_id,
        client_ip=client_ip,
        status_code=status_code,
        response_time_ms=response_time_ms,
        request_size_bytes=request_size_bytes,
        response_size_bytes=response_size_bytes,
        user_agent=user_agent,
        error_message=error_message,
    )
    session.add(usage)
    await session.flush()
    return usage


async def get_api_usage_stats(
    session: AsyncSession,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    endpoint: Optional[str] = None,
    user_id: Optional[UUID] = None,
    limit: int = 1000,
) -> List[Dict[str, Any]]:
    """
    Get API usage statistics.
    
    Returns aggregated stats by endpoint.
    """
    from sqlalchemy import case
    
    stmt = select(
        APIUsage.endpoint,
        APIUsage.method,
        func.count(APIUsage.id).label("total_requests"),
        func.avg(APIUsage.response_time_ms).label("avg_response_time_ms"),
        func.min(APIUsage.response_time_ms).label("min_response_time_ms"),
        func.max(APIUsage.response_time_ms).label("max_response_time_ms"),
        func.sum(
            case((APIUsage.status_code < 400, 1), else_=0)
        ).label("success_count"),
        func.sum(
            case((APIUsage.status_code >= 400, 1), else_=0)
        ).label("error_count"),
    ).group_by(APIUsage.endpoint, APIUsage.method)
    
    if start_date:
        stmt = stmt.where(APIUsage.created_at >= start_date)
    if end_date:
        stmt = stmt.where(APIUsage.created_at <= end_date)
    if endpoint:
        stmt = stmt.where(APIUsage.endpoint == endpoint)
    if user_id:
        stmt = stmt.where(APIUsage.user_id == user_id)
    
    stmt = stmt.order_by(func.count(APIUsage.id).desc()).limit(limit)
    
    result = await session.execute(stmt)
    rows = result.all()
    
    return [
        {
            "endpoint": row.endpoint,
            "method": row.method,
            "total_requests": row.total_requests,
            "avg_response_time_ms": float(row.avg_response_time_ms) if row.avg_response_time_ms else None,
            "min_response_time_ms": row.min_response_time_ms,
            "max_response_time_ms": row.max_response_time_ms,
            "success_count": row.success_count or 0,
            "error_count": row.error_count or 0,
            "success_rate": (row.success_count or 0) / row.total_requests if row.total_requests > 0 else 0,
        }
        for row in rows
    ]


async def get_api_usage_by_endpoint(
    session: AsyncSession,
    endpoint: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 100,
) -> List[APIUsage]:
    """Get API usage records for a specific endpoint."""
    stmt = select(APIUsage).where(APIUsage.endpoint == endpoint)
    
    if start_date:
        stmt = stmt.where(APIUsage.created_at >= start_date)
    if end_date:
        stmt = stmt.where(APIUsage.created_at <= end_date)
    
    stmt = stmt.order_by(APIUsage.created_at.desc()).limit(limit)
    
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_top_endpoints(
    session: AsyncSession,
    limit: int = 10,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    """Get top N most used endpoints."""
    return await get_api_usage_stats(
        session=session,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
    )

