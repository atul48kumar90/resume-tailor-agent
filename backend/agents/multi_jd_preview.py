from agents.ats_scorer import score_detailed
from agents.resume_formatter import format_resume_text


def multi_jd_preview(jds: dict, resume: dict):
    results = {}

    for jd_id, jd_keywords in jds.items():
        results[jd_id] = score_detailed(
            jd_keywords,
            format_resume_text(resume),
        )

    return results
