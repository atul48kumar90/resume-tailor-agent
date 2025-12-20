# agents/ats_scorer.py

from typing import List, Dict


def score(keywords: List[str], resume_text: str) -> Dict:
    """
    Simple ATS keyword match scorer.
    """
    resume_lower = resume_text.lower()

    matched = [k for k in keywords if k.lower() in resume_lower]
    missing = [k for k in keywords if k.lower() not in resume_lower]

    match_percent = int((len(matched) / max(len(keywords), 1)) * 100)

    return {
        "match_percent": match_percent,
        "missing_keywords": missing
    }
