def detect_risk(intent: dict) -> str | None:
    if intent["action"] == "add_skill":
        return (
            "You are adding a skill that may not exist "
            "in your resume. ATS safety may be affected."
        )

    if intent["action"] == "remove_skill":
        return (
            "Removing a core skill may reduce ATS score."
        )

    return None


def preview_chat_edit(resume: dict, intent: dict) -> dict:
    warning = detect_risk(intent)

    simulated = apply_chat_edit(resume, intent)

    return {
        "resume_preview": simulated,
        "warning": warning,
    }
