# agents/jd_analyzer.py
import json
import re
from core.prompts import JD_ANALYZER
from core.llm import smart_llm_call


def _extract_json(text: str) -> dict:
    text = text.strip()

    try:
        return json.loads(text)
    except Exception:
        pass

    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        return json.loads(match.group())

    if '"required_skills"' in text:
        wrapped = "{\n" + text.rstrip(",") + "\n}"
        return json.loads(wrapped)

    raise ValueError("Invalid JSON from LLM")


def analyze_jd(jd: str) -> dict:
    try:
        jd = normalize_jd(jd)
        raw = smart_llm_call(JD_ANALYZER.format(jd=jd))
        data = _extract_json(raw)

        return {
            "required_skills": data.get("required_skills", []),
            "optional_skills": data.get("optional_skills", []),
            "seniority": data.get("seniority", ""),
            "tools": data.get("tools", []),
            "ats_keywords": data.get("ats_keywords", []),
        }

    except Exception as e:
        return {
            "required_skills": [],
            "optional_skills": [],
            "ats_keywords": [],
            "error": str(e),
        }


def normalize_jd(text: str) -> str:
    lines = [
        line.strip()
        for line in text.splitlines()
        if len(line.strip()) > 2
    ]
    return "\n".join(lines)
