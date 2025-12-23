import re


def validate_rewrite(
    rewritten: dict,
    original_resume: str,
    safe_keywords: dict,
) -> dict:
    """
    HARD SAFETY CHECK:
    - Remove hallucinated skills
    - Ensure only allowed keywords exist
    """

    allowed = set(
        safe_keywords.get("explicit", [])
        + [d["skill"] for d in safe_keywords.get("derived", [])]
    )

    original_lower = original_resume.lower()

    # ---- Validate skills section ----
    validated_skills = []
    for skill in rewritten.get("skills", []):
        skill_l = skill.lower()

        if skill in allowed:
            validated_skills.append(skill)
        elif skill_l in original_lower:
            validated_skills.append(skill)
        # else: DROP hallucination

    rewritten["skills"] = validated_skills

    # ---- Validate bullets ----
    for exp in rewritten.get("experience", []):
        safe_bullets = []
        for bullet in exp.get("bullets", []):
            if _bullet_is_safe(bullet, original_lower, allowed):
                safe_bullets.append(bullet)
        exp["bullets"] = safe_bullets

    return rewritten


def _bullet_is_safe(
    bullet: str,
    original_lower: str,
    allowed: set,
) -> bool:
    bullet_l = bullet.lower()

    # If bullet contains new tech words → reject
    tech_terms = re.findall(r"[A-Za-z][A-Za-z0-9.+/#-]{2,}", bullet)
    for term in tech_terms:
        if (
            term not in allowed
            and term.lower() not in original_lower
        ):
            return False

    return True
