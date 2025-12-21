import re
from typing import List, Dict


# -------------------------
# SAFE INFERENCE RULES
# -------------------------

INFERENCE_RULES = {
    "Java": {
        "signals": ["spring boot", "spring framework"],
        "confidence": 0.9,
        "reason": "Spring Boot applications are implemented using Java",
    },
    "REST APIs": {
        "signals": ["designed apis", "developed apis", "rest apis"],
        "confidence": 0.85,
        "reason": "API development implies REST API usage",
    },
}


# -------------------------
# Helpers
# -------------------------

def _extract_sentence(text: str, phrase: str) -> str:
    sentences = re.split(r"[.\n]", text)
    for s in sentences:
        if phrase.lower() in s.lower():
            return s.strip()
    return ""


# -------------------------
# Public API
# -------------------------

def infer_skills_with_evidence(resume_text: str) -> List[Dict]:
    """
    Returns inferred skills with evidence tracing.
    """
    resume_lower = resume_text.lower()
    inferred = []

    for skill, rule in INFERENCE_RULES.items():
        for signal in rule["signals"]:
            if signal in resume_lower:
                inferred.append({
                    "skill": skill,
                    "derived_from": signal,
                    "confidence": rule["confidence"],
                    "evidence_text": _extract_sentence(resume_text, signal),
                    "reason": rule["reason"],
                })
                break

    return inferred
