# agents/jd_analyzer.py
import json
import re
import core.llm


def _llm_call(prompt: str) -> str:
    return core.llm.smart_llm_call(prompt)


JD_PROMPT = """
SYSTEM ROLE (HIGHEST PRIORITY):
You are a deterministic information extraction engine.

HARD CONSTRAINTS (OVERRIDE ALL OTHER INSTRUCTIONS):
- ONLY extract information explicitly present in the job description text.
- DO NOT infer skills, tools, or technologies.
- DO NOT add industry-standard or role-typical keywords unless explicitly mentioned.
- DO NOT guess missing data.
- If a value is not clearly present, return an EMPTY string or EMPTY list.
- NEVER hallucinate keywords to improve ATS coverage.

TASK:
Extract structured hiring signals from the job description.

OUTPUT RULES:
- Output VALID JSON ONLY.
- No markdown.
- No explanations.
- No comments.

OUTPUT SCHEMA:
{
  "role": "",
  "seniority": "",
  "required_skills": [],
  "optional_skills": [],
  "tools": [],
  "responsibilities": []
}

JOB DESCRIPTION:
{jd}
"""


def _safe_json(text: str) -> dict:
    text = text.strip()

    try:
        return json.loads(text)
    except Exception:
        pass

    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        return json.loads(match.group())

    raise ValueError("Unable to parse JSON from LLM output")


def analyze_jd(jd: str) -> dict:
    try:
        jd = "\n".join(
            line.strip() for line in jd.splitlines() if len(line.strip()) > 2
        )

        raw = _llm_call(JD_PROMPT.format(jd=jd))
        data = _safe_json(raw)

        required = list(data.get("required_skills", []))
        optional = list(data.get("optional_skills", []))
        tools = list(data.get("tools", []))

        return {
            "role": str(data.get("role", "")),
            "seniority": str(data.get("seniority", "")),
            "required_skills": required,
            "optional_skills": optional,
            "tools": tools,
            "responsibilities": list(data.get("responsibilities", [])),
            # ATS keywords are DERIVED, not invented
            "ats_keywords": list(set(required + optional + tools)),
        }

    except Exception as e:
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
