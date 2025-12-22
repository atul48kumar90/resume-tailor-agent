# agents/resume_manager.py
"""
Resume management - track multiple resumes, applications, and performance.
"""
import json
import uuid
import logging
import redis
from typing import Dict, List, Optional, Any
from datetime import datetime
from core.settings import (
    REDIS_HOST,
    REDIS_PORT,
    REDIS_DB,
)

logger = logging.getLogger(__name__)

# Redis client for resume management
try:
    redis_client = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DB,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5,
    )
    redis_client.ping()
except Exception as e:
    logger.error(f"Failed to connect to Redis for resume management: {e}")
    redis_client = None

RESUME_TTL = 86400 * 90  # 90 days


def _resume_key(resume_id: str) -> str:
    return f"resume:meta:{resume_id}"


def _resume_list_key(user_id: str = "default") -> str:
    return f"resume:list:{user_id}"


def _application_key(application_id: str) -> str:
    return f"application:{application_id}"


def _application_list_key(resume_id: str) -> str:
    return f"application:list:{resume_id}"


def create_resume(
    resume_data: Dict[str, Any],
    user_id: str = "default",
    title: str = None,
    tags: List[str] = None
) -> str:
    """
    Create a new resume entry in the management system.
    
    Args:
        resume_data: Resume content (structured or text)
        user_id: User identifier
        title: Resume title/name
        tags: Tags for categorization
    
    Returns:
        Resume ID
    """
    if not redis_client:
        raise RuntimeError("Redis not available for resume management")
    
    resume_id = str(uuid.uuid4())
    
    resume_meta = {
        "resume_id": resume_id,
        "user_id": user_id,
        "title": title or f"Resume {datetime.now().strftime('%Y-%m-%d')}",
        "tags": tags or [],
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "version_count": 1,
        "application_count": 0,
        "stats": {
            "total_applications": 0,
            "interviews": 0,
            "rejections": 0,
            "average_ats_score": 0,
        }
    }
    
    # Store resume metadata
    redis_client.setex(
        _resume_key(resume_id),
        RESUME_TTL,
        json.dumps(resume_meta)
    )
    
    # Add to user's resume list
    redis_client.sadd(_resume_list_key(user_id), resume_id)
    redis_client.expire(_resume_list_key(user_id), RESUME_TTL)
    
    logger.info(f"Created resume {resume_id} for user {user_id}")
    return resume_id


def get_resume(resume_id: str) -> Optional[Dict[str, Any]]:
    """Get resume metadata."""
    if not redis_client:
        return None
    
    try:
        data = redis_client.get(_resume_key(resume_id))
        if data:
            return json.loads(data)
    except Exception as e:
        logger.error(f"Error getting resume {resume_id}: {e}")
    
    return None


def list_resumes(user_id: str = "default", tags: List[str] = None) -> List[Dict[str, Any]]:
    """List all resumes for a user, optionally filtered by tags."""
    if not redis_client:
        return []
    
    try:
        resume_ids = redis_client.smembers(_resume_list_key(user_id))
        resumes = []
        
        for resume_id in resume_ids:
            resume = get_resume(resume_id)
            if resume:
                # Filter by tags if provided
                if tags:
                    resume_tags = resume.get("tags", [])
                    if not any(tag in resume_tags for tag in tags):
                        continue
                resumes.append(resume)
        
        # Sort by updated_at (most recent first)
        resumes.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        return resumes
    except Exception as e:
        logger.error(f"Error listing resumes: {e}")
        return []


def update_resume(
    resume_id: str,
    title: str = None,
    tags: List[str] = None,
    stats: Dict[str, Any] = None
):
    """Update resume metadata."""
    if not redis_client:
        return
    
    resume = get_resume(resume_id)
    if not resume:
        raise ValueError(f"Resume {resume_id} not found")
    
    if title:
        resume["title"] = title
    if tags is not None:
        resume["tags"] = tags
    if stats:
        resume["stats"].update(stats)
    
    resume["updated_at"] = datetime.now().isoformat()
    
    redis_client.setex(
        _resume_key(resume_id),
        RESUME_TTL,
        json.dumps(resume)
    )


def create_application(
    resume_id: str,
    jd_text: str,
    jd_title: str = None,
    company: str = None,
    status: str = "applied",
    ats_score: int = None,
    notes: str = None
) -> str:
    """
    Create an application record linking a resume to a job.
    
    Args:
        resume_id: Resume ID
        jd_text: Job description text
        jd_title: Job title
        company: Company name
        status: Application status (applied, interview, rejected, offer)
        ats_score: ATS score for this application
        notes: Optional notes
    
    Returns:
        Application ID
    """
    if not redis_client:
        raise RuntimeError("Redis not available")
    
    application_id = str(uuid.uuid4())
    
    application = {
        "application_id": application_id,
        "resume_id": resume_id,
        "jd_text": jd_text,
        "jd_title": jd_title or "Unknown Position",
        "company": company or "Unknown Company",
        "status": status,
        "ats_score": ats_score,
        "notes": notes,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }
    
    # Store application
    redis_client.setex(
        _application_key(application_id),
        RESUME_TTL,
        json.dumps(application)
    )
    
    # Add to resume's application list
    redis_client.sadd(_application_list_key(resume_id), application_id)
    redis_client.expire(_application_list_key(resume_id), RESUME_TTL)
    
    # Update resume stats
    resume = get_resume(resume_id)
    if resume:
        stats = resume.get("stats", {})
        stats["total_applications"] = stats.get("total_applications", 0) + 1
        
        if ats_score:
            current_avg = stats.get("average_ats_score", 0)
            total = stats.get("total_applications", 1)
            stats["average_ats_score"] = ((current_avg * (total - 1)) + ats_score) / total
        
        if status == "interview":
            stats["interviews"] = stats.get("interviews", 0) + 1
        elif status == "rejected":
            stats["rejections"] = stats.get("rejections", 0) + 1
        
        update_resume(resume_id, stats=stats)
        resume["application_count"] = stats["total_applications"]
        redis_client.setex(
            _resume_key(resume_id),
            RESUME_TTL,
            json.dumps(resume)
        )
    
    logger.info(f"Created application {application_id} for resume {resume_id}")
    return application_id


def list_applications(resume_id: str) -> List[Dict[str, Any]]:
    """List all applications for a resume."""
    if not redis_client:
        return []
    
    try:
        app_ids = redis_client.smembers(_application_list_key(resume_id))
        applications = []
        
        for app_id in app_ids:
            data = redis_client.get(_application_key(app_id))
            if data:
                applications.append(json.loads(data))
        
        # Sort by created_at (most recent first)
        applications.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return applications
    except Exception as e:
        logger.error(f"Error listing applications: {e}")
        return []


def update_application_status(
    application_id: str,
    status: str,
    notes: str = None
):
    """Update application status."""
    if not redis_client:
        return
    
    data = redis_client.get(_application_key(application_id))
    if not data:
        raise ValueError(f"Application {application_id} not found")
    
    application = json.loads(data)
    old_status = application.get("status")
    application["status"] = status
    application["updated_at"] = datetime.now().isoformat()
    
    if notes:
        application["notes"] = notes
    
    redis_client.setex(
        _application_key(application_id),
        RESUME_TTL,
        json.dumps(application)
    )
    
    # Update resume stats if status changed
    if old_status != status:
        resume_id = application.get("resume_id")
        resume = get_resume(resume_id)
        if resume:
            stats = resume.get("stats", {})
            
            # Decrement old status
            if old_status == "interview":
                stats["interviews"] = max(0, stats.get("interviews", 0) - 1)
            elif old_status == "rejected":
                stats["rejections"] = max(0, stats.get("rejections", 0) - 1)
            
            # Increment new status
            if status == "interview":
                stats["interviews"] = stats.get("interviews", 0) + 1
            elif status == "rejected":
                stats["rejections"] = stats.get("rejections", 0) + 1
            
            update_resume(resume_id, stats=stats)


def get_dashboard_stats(user_id: str = "default") -> Dict[str, Any]:
    """Get dashboard statistics for a user."""
    resumes = list_resumes(user_id)
    
    total_resumes = len(resumes)
    total_applications = sum(r.get("stats", {}).get("total_applications", 0) for r in resumes)
    total_interviews = sum(r.get("stats", {}).get("interviews", 0) for r in resumes)
    total_rejections = sum(r.get("stats", {}).get("rejections", 0) for r in resumes)
    
    # Calculate average ATS scores
    ats_scores = [
        r.get("stats", {}).get("average_ats_score", 0)
        for r in resumes
        if r.get("stats", {}).get("average_ats_score", 0) > 0
    ]
    avg_ats_score = sum(ats_scores) / len(ats_scores) if ats_scores else 0
    
    # Calculate interview rate
    interview_rate = (total_interviews / total_applications * 100) if total_applications > 0 else 0
    
    return {
        "total_resumes": total_resumes,
        "total_applications": total_applications,
        "total_interviews": total_interviews,
        "total_rejections": total_rejections,
        "average_ats_score": round(avg_ats_score, 1),
        "interview_rate": round(interview_rate, 1),
        "resumes": [
            {
                "resume_id": r["resume_id"],
                "title": r["title"],
                "tags": r.get("tags", []),
                "application_count": r.get("application_count", 0),
                "average_ats_score": r.get("stats", {}).get("average_ats_score", 0),
                "updated_at": r.get("updated_at")
            }
            for r in resumes[:10]  # Top 10 most recent
        ]
    }

