# agents/resume_risk.py
from typing import Dict, List


def resume_risk_flags(
    jd_keywords: Dict[str, List[str]],
    ats_result: dict,
) -> dict:
    """
    Identifies blocking resume risks based on JD requirements
    """

    missing_required = ats_result.get("missing_required", [])

    flags = []

    if missing_required:
        flags.append({
            "type": "missing_core_skills",
            "severity": "high",
            "details": {
                "missing_skills": missing_required,
                "count": len(missing_required),
            },
            "message": (
                "Resume is missing required skills that are explicitly "
                "listed in the job description."
            ),
        })

    if ats_result["score"] < 60:
        flags.append({
            "type": "low_ats_score",
            "severity": "medium" if ats_result["score"] >= 50 else "high",
            "details": {
                "score": ats_result["score"],
            },
            "message": (
                "ATS score is below the recommended threshold "
                "and may result in automated rejection."
            ),
        })

    return {
        "has_blockers": any(f["severity"] == "high" for f in flags),
        "flags": flags,
    }
