ROLE_TEMPLATE_MAP = {
    "backend": ["classic", "modern"],
    "infra": ["compact", "classic"],
    "frontend": ["modern"],
    "data": ["classic"],
}


def recommend_templates(role_info: dict) -> list[str]:
    role = role_info.get("role", "backend")
    confidence = role_info.get("confidence", 0)

    # Low confidence → safest ATS template
    if confidence < 0.6:
        return ["classic"]

    return ROLE_TEMPLATE_MAP.get(role, ["classic"])
