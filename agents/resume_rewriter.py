# agents/resume_rewriter.py
import json
import re
import core.llm


def _llm_call(prompt: str) -> str:
    return core.llm.smart_llm_call(prompt)


REWRITE_PROMPT = """
SYSTEM ROLE (HIGHEST PRIORITY):
You are a resume editor, NOT a resume generator.

HARD CONSTRAINTS (OVERRIDE ALL OTHER INSTRUCTIONS):
- The ORIGINAL RESUME is the ONLY source of truth.
- You MUST NOT add new skills, tools, technologies, companies, or metrics.
- You MUST NOT infer experience from the job description.
- If a keyword is NOT present or clearly implied in the resume text, DO NOT introduce it.
- Rewriting = rephrasing, clarifying, or reordering ONLY.

TASK:
Rewrite the resume to better surface EXISTING overlaps with the job description.

PROCESS (DO NOT OUTPUT):
1. Identify keywords already present in the resume.
2. Rephrase bullets to highlight those keywords.
3. Preserve original meaning exactly.
4. Drop content that cannot be rewritten safely.

OUTPUT RULES:
- Output VALID JSON ONLY.
- No explanations.
- No markdown.

OUTPUT FORMAT:
{
  "summary": "",
  "experience": [
    {
      "title": "",
      "bullets": []
    }
  ],
  "skills": []
}

JOB DESCRIPTION (REFERENCE ONLY — DO NOT COPY FROM HERE):
{keywords}

ORIGINAL RESUME (ONLY SOURCE OF TRUTH):
{resume}
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


def rewrite(jd: str, resume: str) -> dict:
    try:
        raw = _llm_call(
            REWRITE_PROMPT.format(
                keywords=jd,
                resume=resume,
            )
        )

        data = _safe_json(raw)

        return {
            "summary": str(data.get("summary", "")),
            "experience": list(data.get("experience", [])),
            "skills": list(data.get("skills", [])),
        }

    except Exception as e:
        return {
            "summary": "",
            "experience": [],
            "skills": [],
            "error": str(e),
        }
