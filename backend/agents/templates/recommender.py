ROLE_TEMPLATE_MAP = {
    "backend": ["technical", "classic", "modern"],
    "frontend": ["modern", "technical", "creative"],
    "infra": ["compact", "classic", "technical"],
    "devops": ["technical", "compact", "classic"],
    "sre": ["technical", "classic"],
    "data": ["classic", "technical", "academic"],
    "data-scientist": ["academic", "technical", "classic"],
    "software-engineer": ["technical", "modern", "classic"],
    "executive": ["executive", "classic"],
    "c-suite": ["executive", "classic"],
    "director": ["executive", "classic"],
    "vp": ["executive", "classic"],
    "senior-management": ["executive", "classic"],
    "designer": ["creative", "modern"],
    "artist": ["creative"],
    "writer": ["creative", "modern"],
    "photographer": ["creative"],
    "creative-director": ["creative", "executive"],
    "researcher": ["academic", "classic"],
    "professor": ["academic"],
    "scientist": ["academic", "technical"],
    "phd": ["academic", "classic"],
    "postdoc": ["academic"],
    "entry-level": ["compact", "minimal", "classic"],
    "career-change": ["compact", "classic"],
    "students": ["compact", "minimal"],
    "recent-graduates": ["compact", "minimal", "classic"],
    "corporate": ["classic", "executive"],
    "finance": ["classic", "executive"],
    "legal": ["classic", "executive"],
    "tech": ["modern", "technical", "classic"],
    "startup": ["modern", "creative", "technical"],
    "marketing": ["modern", "creative"],
}


def recommend_templates(role_info: dict) -> list[str]:
    """
    Recommend templates based on role information.
    
    Args:
        role_info: Dictionary with role, confidence, and signals
    
    Returns:
        List of recommended template IDs (ordered by relevance)
    """
    role = role_info.get("role", "backend")
    confidence = role_info.get("confidence", 0)

    # Low confidence → safest ATS template
    if confidence < 0.6:
        return ["classic", "minimal"]

    # Get role-specific recommendations
    recommendations = ROLE_TEMPLATE_MAP.get(role, ["classic"])
    
    # Always include classic as fallback
    if "classic" not in recommendations:
        recommendations.append("classic")
    
    return recommendations


def recommend_templates_by_industry(industry: str) -> list[str]:
    """
    Recommend templates based on industry.
    
    Args:
        industry: Industry name
    
    Returns:
        List of recommended template IDs
    """
    industry_map = {
        "technology": ["modern", "technical", "classic"],
        "finance": ["classic", "executive"],
        "healthcare": ["classic", "academic"],
        "education": ["academic", "classic"],
        "creative": ["creative", "modern"],
        "legal": ["classic", "executive"],
        "consulting": ["executive", "classic"],
        "nonprofit": ["classic", "modern"],
    }
    
    return industry_map.get(industry.lower(), ["classic", "minimal"])


def get_template_for_experience_level(years_of_experience: float) -> str:
    """
    Recommend template based on years of experience.
    
    Args:
        years_of_experience: Years of professional experience
    
    Returns:
        Recommended template ID
    """
    if years_of_experience < 2:
        return "compact"
    elif years_of_experience < 5:
        return "classic"
    elif years_of_experience < 10:
        return "modern"
    else:
        return "executive"
