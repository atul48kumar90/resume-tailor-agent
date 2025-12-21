# agents/resume_rewriter.py
import json
import re
import core.llm
from typing import Dict, List


# -------------------------------------------------
# LLM call wrapper
# -------------------------------------------------

def _llm_call(prompt: str) -> str:
    return core.llm.smart_llm_call(prompt)


# -------------------------------------------------
# Rewrite Prompt (STRICT + SAFE)
# -------------------------------------------------

REWRITE_PROMPT = """
SYSTEM ROLE (HIGHEST PRIORITY):
You are a resume editor, NOT a resume generator.

HARD CONSTRAINTS (OVERRIDE ALL OTHER INSTRUCTIONS):
- The ORIGINAL RESUME is the primary source of truth.
- You MUST NOT invent experience, companies, domains, or metrics.
- You MUST NOT exaggerate seniority or scope.
- You MAY surface keywords ONLY if explicitly allowed below.
- Derived keywords MUST be phrased conservatively.

TASK:
Rewrite the resume to better surface role-relevant skills
without changing factual meaning.

SAFE KEYWORDS (STRICTLY CONTROLLED):
- EXPLICIT: already present in resume
- DERIVED: logically implied (allowed, conservative phrasing only)

ALLOWED KEYWORDS (DO NOT EXCEED):
{allowed_keywords}

RULES:
- Rewriting = rephrasing, clarifying, or reordering ONLY
- If a bullet cannot be improved safely, KEEP it unchanged
- No keyword stuffing
- No new claims

OUTPUT JSON ONLY:
{{
  "summary": "",
  "experience": [
    {{
      "title": "",
      "bullets": []
    }}
  ],
  "skills": []
}}

ORIGINAL RESUME:
{resume}
"""


# -------------------------------------------------
# JSON safety
# -------------------------------------------------

def _safe_json(text: str) -> dict:
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        raise ValueError("No JSON found in LLM output")
    return json.loads(match.group())


# -------------------------------------------------
# Confidence-based keyword formatting
# -------------------------------------------------

def format_allowed_keywords(jd_keywords: dict) -> dict:
    explicit: List[str] = jd_keywords.get("explicit", [])
    derived_out: List[str] = []

    for item in jd_keywords.get("derived", []):
        skill = item.get("skill")
        confidence = item.get("confidence", 0)

        if not skill:
            continue

        if confidence >= 0.9:
            derived_out.append(skill)
        elif confidence >= 0.75:
            derived_out.append(f"{skill} (related experience)")

    return {
        "explicit": explicit,
        "derived": derived_out,
    }


# -------------------------------------------------
# 🔒 Post-LLM validation (FIXED)
# -------------------------------------------------

def validate_rewrite(
    rewritten: dict,
    original_resume: str,
    allowed_keywords: dict,
    baseline_keywords: Dict[str, List[str]] | None = None,
) -> dict:
    """
    Hard safety net with ATS preservation.
    """

    original_lower = original_resume.lower()

    allowed_flat = set(
        allowed_keywords.get("explicit", [])
        + allowed_keywords.get("derived", [])
    )

    baseline_flat = set()
    if baseline_keywords:
        for v in baseline_keywords.values():
            baseline_flat.update(v)

    def safe_text(text: str) -> bool:
        """
        Accept if:
        - phrase existed in original resume
        - OR contains allowed keyword
        - OR contains baseline ATS keyword
        """
        text_l = text.lower()

        if text_l in original_lower:
            return True

        for kw in allowed_flat | baseline_flat:
            if kw.lower() in text_l:
                return True

        return False

    # Summary
    if not safe_text(rewritten.get("summary", "")):
        rewritten["summary"] = ""

    # Experience bullets
    for exp in rewritten.get("experience", []):
        safe_bullets = []
        for bullet in exp.get("bullets", []):
            if safe_text(bullet):
                safe_bullets.append(bullet)
        exp["bullets"] = safe_bullets

    # Skills section
    rewritten["skills"] = list(
        dict.fromkeys(
            [
                s for s in rewritten.get("skills", [])
                if (
                    s in allowed_flat
                    or s in baseline_flat
                )
            ]
        )
    )

    return rewritten


# -------------------------------------------------
# Main rewrite function
# -------------------------------------------------

def rewrite(
    jd_keywords: dict,
    resume: str,
    baseline_keywords: Dict[str, List[str]] | None = None,
) -> dict:
    """
    baseline_keywords = matched keywords BEFORE rewrite
    """

    try:
        safe_keywords = format_allowed_keywords(jd_keywords)

        raw = _llm_call(
            REWRITE_PROMPT.format(
                allowed_keywords=json.dumps(
                    safe_keywords,
                    indent=2,
                ),
                resume=resume,
            )
        )

        data = _safe_json(raw)

        rewritten = {
            "summary": str(data.get("summary", "")),
            "experience": list(data.get("experience", [])),
            "skills": list(data.get("skills", [])),
        }

        # 🔒 Final validation
        rewritten = validate_rewrite(
            rewritten,
            resume,
            safe_keywords,
            baseline_keywords,
        )

        return rewritten

    except Exception as e:
        return {
            "summary": "",
            "experience": [],
            "skills": [],
            "error": str(e),
        }
