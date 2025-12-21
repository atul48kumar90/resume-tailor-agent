# core/prompts.py

JD_ANALYZER = """
You are a job description analysis engine.

Extract the following as JSON:
- required_skills
- optional_skills
- seniority
- tools
- ats_keywords

Rules:
- Do NOT invent skills
- Extract only what is explicitly mentioned

Job Description:
{jd}

Output JSON only.
"""


RESUME_REWRITE_PROMPT = """
You are a professional resume rewriting engine.

Rules:
- Do NOT add skills or experience
- Do NOT invent metrics
- Improve clarity and ATS alignment only

Job Description:
{job_description}

Resume:
{resume}

Return JSON:
{
  "summary": "",
  "experience": [],
  "skills": []
}
"""
