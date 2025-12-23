# agents/jd_fit.py
from typing import Dict


def classify_jd_fit(ats_result: Dict) -> dict:
    score = ats_result.get("score", 0)
    missing_required = ats_result.get("missing_required", [])

    if score >= 75 and not missing_required:
        fit = "strong"
        explanation = (
            "Resume strongly matches the job description with good ATS coverage "
            "and no missing required skills."
        )

    elif score >= 55 and len(missing_required) <= 1:
        fit = "partial"
        explanation = (
            "Resume partially matches the job description. Some required skills "
            "or ATS coverage gaps may reduce shortlisting chances."
        )

    else:
        fit = "weak"
        explanation = (
            "Resume is a weak fit for the job description due to low ATS coverage "
            "or multiple missing required skills."
        )

    return {
        "fit": fit,
        "score": score,
        "missing_required_count": len(missing_required),
        "explanation": explanation,
    }
