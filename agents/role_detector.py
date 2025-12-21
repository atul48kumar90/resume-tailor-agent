import re
from typing import Dict


ROLE_KEYWORDS = {
    "backend": [
        "java", "spring", "spring boot", "rest", "api",
        "microservices", "backend", "distributed",
        "data structures", "algorithms", "j2ee"
    ],
    "infra": [
        "kubernetes", "docker", "terraform", "aws",
        "gcp", "azure", "ci/cd", "helm", "devops",
        "monitoring", "prometheus", "grafana"
    ],
    "frontend": [
        "react", "angular", "vue", "javascript",
        "typescript", "html", "css", "frontend"
    ],
}


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9]", " ", text.lower())


def detect_role(jd_text: str, resume_text: str) -> Dict:
    """
    Deterministic role detection.
    No LLM. No hallucination risk.
    """

    text = _normalize(jd_text + " " + resume_text)
    tokens = set(text.split())

    signals = {role: 0 for role in ROLE_KEYWORDS}

    for role, keywords in ROLE_KEYWORDS.items():
        for kw in keywords:
            if kw in tokens:
                signals[role] += 1

    # Pick dominant role
    role = max(signals, key=signals.get)
    total = sum(signals.values()) or 1
    confidence = round(signals[role] / total, 2)

    # Backend + Infra both strong → fullstack/platform
    if signals["backend"] >= 5 and signals["infra"] >= 5:
        role = "fullstack"

    return {
        "role": role,
        "confidence": confidence,
        "signals": signals,
    }
