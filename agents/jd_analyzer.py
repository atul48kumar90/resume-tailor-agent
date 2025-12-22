# agents/jd_analyzer.py
import json
import re
import core.llm
from typing import Dict, Any


# ------------------------
# LLM wrapper (mockable)
# ------------------------

def _llm_call(prompt: str) -> str:
    return core.llm.smart_llm_call(prompt)


# ------------------------
# PROMPT (AS-IS, UNCHANGED)
# ------------------------

JD_PROMPT = """
You are a senior technical recruiter and ATS optimization expert.

TASK:
Analyze the job description and extract structured hiring signals.

STRICT RULES:
- Use ONLY information present or clearly implied in the job description
- Do NOT invent skills, tools, or experience
- Prefer technical, role-specific keywords
- Normalize similar terms (e.g., "Spring" → "Spring Boot")

CLASSIFY SKILLS AS:
- Required skills: explicitly required
- Optional skills: nice-to-have or implied
- Tools: platforms, frameworks, infrastructure
- Responsibilities: concrete job duties

ATS KEYWORDS:
- Include commonly expected keywords for this role
- Only if they are relevant to the JD context

OUTPUT FORMAT:
Return VALID JSON ONLY with the following keys:
role, seniority, required_skills, optional_skills, tools, responsibilities, ats_keywords

JOB DESCRIPTION:
{jd}
"""


# ------------------------
# Ultra-defensive JSON parser
# ------------------------

def _safe_json(text: str) -> Dict[str, Any]:
    if not text or not isinstance(text, str):
        raise ValueError("Empty or invalid LLM response")

    # Extract first JSON object
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        raise ValueError("No JSON object found in LLM output")

    raw = match.group()

    # Fix common LLM formatting errors
    raw = raw.replace("\n", " ")
    raw = re.sub(r",\s*}", "}", raw)
    raw = re.sub(r",\s*]", "]", raw)

    data = json.loads(raw)

    if isinstance(data, list):
        if not data:
            raise ValueError("Empty JSON list returned")
        data = data[0]

    if not isinstance(data, dict):
        raise ValueError("Parsed JSON is not an object")

    return data


# ------------------------
# Schema normalization (CRITICAL FIX)
# ------------------------

def _normalize_schema(data: Dict[str, Any]) -> Dict[str, list]:
    """
    Protects against LLM key drift:
    role vs job_role, required_skills vs requirements, etc.
    """

    key_map = {
        "role": ["role", "job_role", "position"],
        "seniority": ["seniority", "level", "experience_level"],
        "required_skills": ["required_skills", "requirements", "must_have_skills"],
        "optional_skills": ["optional_skills", "nice_to_have", "preferred_skills"],
        "tools": ["tools", "technologies", "platforms"],
        "responsibilities": ["responsibilities", "duties"],
        "ats_keywords": ["ats_keywords", "keywords"],
    }

    normalized = {}
    for target, aliases in key_map.items():
        value = []
        for alias in aliases:
            if alias in data and data[alias]:
                value = data[alias]
                break
        normalized[target] = list(value) if isinstance(value, list) else value

    return normalized


# ------------------------
# Public API
# ------------------------

def analyze_jd(jd: str) -> dict:
    try:
        # Clean JD input
        jd = "\n".join(
            line.strip()
            for line in jd.splitlines()
            if len(line.strip()) > 2
        )

        raw = _llm_call(JD_PROMPT.format(jd=jd))
        parsed = _safe_json(raw)
        data = _normalize_schema(parsed)

        # Auto-build ATS keywords if missing
        if not data["ats_keywords"]:
            data["ats_keywords"] = list(
                set(
                    data["required_skills"]
                    + data["optional_skills"]
                    + data["tools"]
                )
            )

        return {
            "role": str(data["role"]),
            "seniority": str(data["seniority"]),
            "required_skills": data["required_skills"],
            "optional_skills": data["optional_skills"],
            "tools": data["tools"],
            "responsibilities": data["responsibilities"],
            "ats_keywords": data["ats_keywords"],
        }

    except Exception as e:
        # Log error with context
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"JD analysis failed: {e}", exc_info=True)
        
        # Hard fail-safe - return empty structure but log the error
        return {
            "role": "",
            "seniority": "",
            "required_skills": [],
            "optional_skills": [],
            "tools": [],
            "responsibilities": [],
            "ats_keywords": [],
            "error": str(e),
        }
