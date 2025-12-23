# agents/keyword_confidence.py
from typing import Dict, List
from agents.ats_scorer import _tokenize, _match_keyword


def keyword_confidence(
    jd_keywords: Dict[str, List[str]],
    resume_text: str,
) -> Dict[str, Dict[str, List[str]]]:
    """
    Returns keywords grouped by confidence level
    """
    tokens = _tokenize(resume_text)

    high = {"required_skills": [], "optional_skills": [], "tools": []}
    medium = {"required_skills": [], "optional_skills": [], "tools": []}
    low = {"required_skills": [], "optional_skills": [], "tools": []}

    for category, keywords in jd_keywords.items():
        for kw in keywords:
            if _match_keyword(kw, tokens):
                high[category].append(kw)
            else:
                # Partial token overlap → medium confidence
                kw_tokens = set(_tokenize(kw))
                overlap = kw_tokens & tokens

                if overlap:
                    medium[category].append(kw)
                else:
                    low[category].append(kw)

    return {
        "high": high,
        "medium": medium,
        "low": low,
    }
