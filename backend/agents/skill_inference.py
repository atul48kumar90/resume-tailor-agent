from typing import List, Dict


# =========================================================
# DEFAULT BACKEND INFERENCE RULES
# =========================================================

INFERENCE_RULES = [
    # -------- Core Backend --------
    {
        "derived": "Java",
        "requires": ["spring boot"],
        "base_confidence": 0.9,
    },
    {
        "derived": "HTTP",
        "requires": ["rest api", "rest apis"],
        "base_confidence": 0.95,
    },
    {
        "derived": "Distributed Systems",
        "requires": ["microservices", "scalable"],
        "base_confidence": 0.85,
    },
    {
        "derived": "Cloud Architecture",
        "requires": ["aws", "deployment", "scaling"],
        "base_confidence": 0.8,
    },

    # -------- Data --------
    {
        "derived": "Relational Databases",
        "requires": ["sql", "schema"],
        "base_confidence": 0.8,
    },
    {
        "derived": "NoSQL Databases",
        "requires": ["redis", "dynamodb"],
        "base_confidence": 0.9,
    },

    # -------- Infra / Ops --------
    {
        "derived": "CI/CD",
        "requires": ["github actions", "bamboo", "pipeline"],
        "base_confidence": 0.85,
    },
    {
        "derived": "Monitoring & Observability",
        "requires": ["uptime", "alerts", "monitoring"],
        "base_confidence": 0.75,
    },
]


# =========================================================
# INFERENCE ENGINE
# =========================================================

def infer_skills_from_resume(
    resume_text: str,
    explicit_skills: List[str],
) -> List[Dict]:
    """
    Returns derived skills with evidence + confidence
    """
    resume_lower = resume_text.lower()
    explicit_lower = {s.lower() for s in explicit_skills}

    inferred = []

    for rule in INFERENCE_RULES:
        # Avoid duplication
        if rule["derived"].lower() in explicit_lower:
            continue

        hits = [
            kw for kw in rule["requires"]
            if kw in resume_lower
        ]

        if hits:
            inferred.append({
                "skill": rule["derived"],
                "confidence": rule["base_confidence"],
                "evidence": hits,
            })

    return inferred
