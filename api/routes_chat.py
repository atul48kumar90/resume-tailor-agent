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

router = APIRouter(prefix="/resume/chat")


@router.post("/message")
def chat_edit(message: str):
    """
    User sends chat instruction like:
    - Add Java
    - Rewrite second bullet
    """

    current = get_current_version()

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


@router.post("/apply")
def apply_chat_edit_api(intent: dict):
    current = get_current_version()

    updated = apply_chat_edit(
        resume=current["resume"],
        intent=intent,
    )

    save_new_version(
        parent=current["version_id"],
        resume=updated,
        change_summary=intent["summary"],
    )

    return {"status": "applied"}


@router.post("/undo")
def undo():
    return undo_version()


@router.post("/redo")
def redo():
    return redo_version()


@router.post("/preview/ats")
def ats_preview(intent: dict):
    current = get_current_version()
    simulated = apply_chat_edit(current["resume"], intent)

    return preview_ats_change(
        jd_keywords=current["jd_keywords"],
        resume_before=current["resume"],
        resume_after=simulated,
    )


@router.post("/chat/preview/multi-jd")
def preview_multi_jd(intent: dict):
    current = get_current_version()
    simulated = apply_chat_edit(current["resume"], intent)

    return multi_jd_preview(
        jds=current["jd_sets"],
        resume=simulated,
    )
