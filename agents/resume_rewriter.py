# agents/resume_rewriter.py
import json
import re
from core.llm import smart_llm_call
from core.prompts import RESUME_REWRITE_PROMPT


def _extract_json(text: str) -> dict:
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        raise ValueError("Invalid JSON")

    return json.loads(match.group())


def rewrite(job_description: str, resume: str) -> dict:
    try:
        raw = smart_llm_call(
            RESUME_REWRITE_PROMPT.format(
                job_description=job_description,
                resume=resume
            )
        )
        data = _extract_json(raw)

        return {
            "summary": data.get("summary", ""),
            "experience": data.get("experience", []),
            "skills": data.get("skills", []),
        }

    except Exception as e:
        return {
            "summary": "",
            "experience": [],
            "skills": [],
            "error": str(e),
        }
