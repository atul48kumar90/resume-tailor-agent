ROLE_CONFIDENCE_MULTIPLIERS = {
    "backend": {
        "Java": 1.0,
        "HTTP": 1.0,
        "Distributed Systems": 1.0,
        "Cloud Architecture": 0.95,
        "CI/CD": 0.9,
    },
    "infra": {
        "Java": 0.6,
        "HTTP": 0.7,
        "Distributed Systems": 0.85,
        "Cloud Architecture": 1.0,
        "CI/CD": 1.0,
    },
    "fullstack": {
        "Java": 0.85,
        "HTTP": 1.0,
        "Distributed Systems": 0.85,
        "Cloud Architecture": 0.85,
        "CI/CD": 0.9,
    },
}


def tune_confidence_by_role(
    inferred_skills: list[dict],
    role: str,
) -> list[dict]:
    multipliers = ROLE_CONFIDENCE_MULTIPLIERS.get(
        role.lower(),
        {}
    )

    tuned = []

    for skill in inferred_skills:
        multiplier = multipliers.get(skill["skill"], 1.0)
        tuned.append({
            **skill,
            "confidence": round(skill["confidence"] * multiplier, 2),
        })

    return tuned
