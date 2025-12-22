import json
import core.llm


INTENT_PROMPT = """
You are a resume edit intent parser.

Convert the user request into a STRUCTURED COMMAND.
DO NOT edit resume text.

Allowed actions:
- add_skill
- remove_skill
- rewrite_bullet
- rewrite_summary

Output JSON ONLY.

User message:
{message}
"""


def parse_chat_intent(message: str) -> dict:
    raw = core.llm.smart_llm_call(
        INTENT_PROMPT.format(message=message)
    )
    return json.loads(raw)


def apply_chat_edit(resume: dict, intent: dict) -> dict:
    resume = resume.copy()

    action = intent["action"]

    if action == "add_skill":
        skill = intent["skill"]
        if skill not in resume["skills"]:
            resume["skills"].append(skill)

    elif action == "remove_skill":
        resume["skills"] = [
            s for s in resume["skills"]
            if s != intent["skill"]
        ]

    elif action == "rewrite_bullet":
        idx = intent["index"]
        resume["experience"][intent["exp_index"]]["bullets"][idx] = (
            _rewrite_text(
                resume["experience"][intent["exp_index"]]["bullets"][idx]
            )
        )

    return resume


def _rewrite_text(text: str) -> str:
    prompt = f"""
Rewrite this resume bullet for clarity.
Do NOT add skills, metrics, or claims.

{text}
"""
    return core.llm.smart_llm_call(prompt).strip()


def preview_chat_edit(resume: dict, intent: dict) -> dict:
    simulated = apply_chat_edit(resume, intent)

    return {
        "resume_preview": simulated,
        "requires_approval": intent.get("requires_approval", False),
        "risk_level": intent.get("risk_level", "low"),
        "approval_message": (
            "This change may impact ATS score. Approve?"
            if intent.get("requires_approval")
            else None
        ),
    }
