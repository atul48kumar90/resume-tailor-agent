import json
from core.llm import get_llm

llm = get_llm()


def rewrite(jd: str, resume: str) -> dict:
    """
    Rewrite resume to align with job description.
    Minimal implementation for now.
    """

    prompt = f"""
    You are a resume rewriting assistant.

    Rules:
    - Do NOT add fake experience
    - Only rewrite based on provided resume
    - Optimize wording for ATS

    Job Description:
    {jd}

    Resume:
    {resume}

    Return STRICT JSON:
    {{
      "summary": "",
      "experience": [],
      "skills": []
    }}
    """

    response = llm.predict(prompt)
    return json.loads(response)
