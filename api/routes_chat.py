from fastapi import APIRouter, HTTPException
from agents.resume_chat_editor import (
    parse_chat_intent,
    apply_chat_edit,
    preview_chat_edit,
)
from agents.resume_versions import (
    get_current_version,
    save_new_version,
    undo_version,
    redo_version,
)
from agents.chat_ats_preview import preview_ats_change
from agents.multi_jd_preview import multi_jd_preview
from api.schemas import ChatIntentRequest
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/resume/chat")


@router.post("/{resume_id}/message")
def chat_edit(resume_id: str, message: str):
    """
    User sends chat instruction like:
    - Add Java
    - Rewrite second bullet
    
    Args:
        resume_id: Unique identifier for the resume session
        message: Natural language instruction
    """
    if not message or not message.strip():
        raise HTTPException(
            status_code=400,
            detail="Message cannot be empty"
        )

    current = get_current_version(resume_id)
    if not current:
        raise HTTPException(
            status_code=404,
            detail=f"Resume session {resume_id} not found"
        )

    try:
        intent = parse_chat_intent(message)

        preview = preview_chat_edit(
            resume=current["resume"],
            intent=intent,
        )

        return {
            "intent": intent,
            "preview": preview,
            "warning": preview.get("warning"),
        }
    except Exception as e:
        logger.error(f"Chat edit failed for resume {resume_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process chat message: {str(e)}"
        )


@router.post("/{resume_id}/apply")
def apply_chat_edit_api(resume_id: str, intent: ChatIntentRequest):
    """
    Apply a chat edit to the resume.
    
    Args:
        resume_id: Unique identifier for the resume session
        intent: Structured edit intent
    """
    current = get_current_version(resume_id)
    if not current:
        raise HTTPException(
            status_code=404,
            detail=f"Resume session {resume_id} not found"
        )

    try:
        updated = apply_chat_edit(
            resume=current["resume"],
            intent=intent.dict(),
        )

        version_id = save_new_version(
            resume_id=resume_id,
            parent=current["version_id"],
            resume=updated,
            change_summary=intent.summary or "Chat edit applied",
        )
        
        if not version_id:
            raise HTTPException(
                status_code=500,
                detail="Failed to save version"
            )

        return {"status": "applied", "version_id": version_id}
    except Exception as e:
        logger.error(f"Failed to apply chat edit for resume {resume_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to apply edit: {str(e)}"
        )


@router.post("/{resume_id}/undo")
def undo(resume_id: str):
    """Undo last change to resume."""
    version = undo_version(resume_id)
    if not version:
        raise HTTPException(
            status_code=404,
            detail="No previous version to undo to"
        )
    return version


@router.post("/{resume_id}/redo")
def redo(resume_id: str):
    """Redo last undone change to resume."""
    version = redo_version(resume_id)
    if not version:
        raise HTTPException(
            status_code=404,
            detail="No next version to redo to"
        )
    return version


@router.post("/{resume_id}/preview/ats")
def ats_preview(resume_id: str, intent: ChatIntentRequest):
    """Preview ATS score change before applying edit."""
    current = get_current_version(resume_id)
    if not current:
        raise HTTPException(
            status_code=404,
            detail=f"Resume session {resume_id} not found"
        )
    
    if "jd_keywords" not in current:
        raise HTTPException(
            status_code=400,
            detail="JD keywords not found in current version"
        )
    
    simulated = apply_chat_edit(current["resume"], intent.dict())

    return preview_ats_change(
        jd_keywords=current["jd_keywords"],
        resume_before=current["resume"],
        resume_after=simulated,
    )


@router.post("/{resume_id}/preview/multi-jd")
def preview_multi_jd(resume_id: str, intent: ChatIntentRequest):
    """Preview ATS scores across multiple JDs before applying edit."""
    current = get_current_version(resume_id)
    if not current:
        raise HTTPException(
            status_code=404,
            detail=f"Resume session {resume_id} not found"
        )
    
    if "jd_sets" not in current:
        raise HTTPException(
            status_code=400,
            detail="JD sets not found in current version"
        )
    
    simulated = apply_chat_edit(current["resume"], intent.dict())

    return multi_jd_preview(
        jds=current["jd_sets"],
        resume=simulated,
    )
