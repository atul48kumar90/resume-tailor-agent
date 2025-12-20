# core/prompts.py
JD_ANALYZER = """
Analyze the job description and extract:
- required_skills
- optional_skills
- seniority
- tools
- ats_keywords

Return STRICT JSON.

Job Description:
{jd}
"""
