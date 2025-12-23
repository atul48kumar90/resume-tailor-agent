from typing import Dict, List, Optional

# Template schema definition
TEMPLATE_SCHEMA = {
    "name": str,
    "description": str,
    "font": str,
    "heading_size": int,
    "body_size": int,
    "line_spacing": int,
    "section_spacing": int,
    "accent": bool,
    "color_scheme": str,  # "monochrome", "blue", "green", "professional"
    "layout": str,  # "single-column", "two-column", "hybrid"
    "ats_friendly": bool,
    "best_for": List[str],  # Roles/industries this template is best for
    "sections": List[str],  # Available sections
}

TEMPLATES: Dict[str, dict] = {
    "classic": {
        "name": "Classic ATS",
        "description": "Traditional, highly ATS-friendly format. Best for all industries.",
        "font": "Helvetica",
        "heading_size": 14,
        "body_size": 10,
        "line_spacing": 8,
        "section_spacing": 14,
        "accent": False,
        "color_scheme": "monochrome",
        "layout": "single-column",
        "ats_friendly": True,
        "best_for": ["all", "corporate", "finance", "legal"],
        "sections": ["summary", "experience", "education", "skills", "certifications"],
    },
    "modern": {
        "name": "Modern Clean",
        "description": "Clean, contemporary design with subtle accents. ATS-friendly with modern appeal.",
        "font": "Helvetica-Bold",
        "heading_size": 15,
        "body_size": 10,
        "line_spacing": 9,
        "section_spacing": 16,
        "accent": True,
        "color_scheme": "blue",
        "layout": "single-column",
        "ats_friendly": True,
        "best_for": ["tech", "startup", "design", "marketing"],
        "sections": ["summary", "experience", "education", "skills", "projects"],
    },
    "compact": {
        "name": "Compact One-Page",
        "description": "Space-efficient design for one-page resumes. Perfect for entry-level or career changers.",
        "font": "Helvetica",
        "heading_size": 13,
        "body_size": 9,
        "line_spacing": 6,
        "section_spacing": 10,
        "accent": False,
        "color_scheme": "monochrome",
        "layout": "single-column",
        "ats_friendly": True,
        "best_for": ["entry-level", "career-change", "students", "recent-graduates"],
        "sections": ["summary", "experience", "education", "skills"],
    },
    "executive": {
        "name": "Executive Professional",
        "description": "Sophisticated design for senior roles. Emphasizes leadership and achievements.",
        "font": "Times-Roman",
        "heading_size": 16,
        "body_size": 11,
        "line_spacing": 10,
        "section_spacing": 18,
        "accent": True,
        "color_scheme": "professional",
        "layout": "single-column",
        "ats_friendly": True,
        "best_for": ["executive", "c-suite", "director", "vp", "senior-management"],
        "sections": ["summary", "experience", "education", "skills", "certifications", "awards"],
    },
    "technical": {
        "name": "Technical Professional",
        "description": "Optimized for technical roles. Highlights skills and technical achievements.",
        "font": "Courier",
        "heading_size": 14,
        "body_size": 10,
        "line_spacing": 8,
        "section_spacing": 14,
        "accent": False,
        "color_scheme": "monochrome",
        "layout": "two-column",  # Skills in sidebar
        "ats_friendly": True,
        "best_for": ["software-engineer", "data-scientist", "devops", "sre", "backend", "frontend"],
        "sections": ["summary", "experience", "skills", "education", "projects", "certifications"],
    },
    "creative": {
        "name": "Creative Portfolio",
        "description": "Design-forward template for creative professionals. Balanced ATS compatibility with visual appeal.",
        "font": "Helvetica",
        "heading_size": 16,
        "body_size": 10,
        "line_spacing": 10,
        "section_spacing": 20,
        "accent": True,
        "color_scheme": "green",
        "layout": "hybrid",
        "ats_friendly": True,  # Still ATS-friendly despite creative design
        "best_for": ["designer", "artist", "writer", "photographer", "creative-director"],
        "sections": ["summary", "experience", "projects", "skills", "education"],
    },
    "academic": {
        "name": "Academic CV",
        "description": "Formal format for academic and research positions. Emphasizes publications and research.",
        "font": "Times-Roman",
        "heading_size": 14,
        "body_size": 10,
        "line_spacing": 8,
        "section_spacing": 14,
        "accent": False,
        "color_scheme": "monochrome",
        "layout": "single-column",
        "ats_friendly": True,
        "best_for": ["researcher", "professor", "scientist", "phd", "postdoc"],
        "sections": ["summary", "education", "experience", "publications", "research", "skills"],
    },
    "minimal": {
        "name": "Minimal ATS",
        "description": "Ultra-minimal design. Maximum ATS compatibility with clean aesthetics.",
        "font": "Helvetica",
        "heading_size": 12,
        "body_size": 9,
        "line_spacing": 7,
        "section_spacing": 12,
        "accent": False,
        "color_scheme": "monochrome",
        "layout": "single-column",
        "ats_friendly": True,
        "best_for": ["all", "minimalist", "ats-focused"],
        "sections": ["summary", "experience", "education", "skills"],
    },
}


def get_template(template_id: str) -> Optional[dict]:
    """Get template by ID."""
    return TEMPLATES.get(template_id)


def list_templates() -> List[dict]:
    """List all available templates with metadata."""
    return [
        {
            "id": template_id,
            "name": template["name"],
            "description": template["description"],
            "ats_friendly": template["ats_friendly"],
            "best_for": template["best_for"],
            "color_scheme": template["color_scheme"],
            "layout": template["layout"],
        }
        for template_id, template in TEMPLATES.items()
    ]


def get_template_details(template_id: str) -> Optional[dict]:
    """Get full template details including all configuration."""
    template = TEMPLATES.get(template_id)
    if template:
        return {
            "id": template_id,
            **template
        }
    return None


def validate_template_config(config: dict) -> tuple[bool, Optional[str]]:
    """
    Validate a custom template configuration.
    
    Args:
        config: Template configuration dictionary
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    required_fields = ["name", "font", "heading_size", "body_size", "line_spacing", "section_spacing"]
    
    for field in required_fields:
        if field not in config:
            return False, f"Missing required field: {field}"
    
    # Validate types
    if not isinstance(config["name"], str):
        return False, "name must be a string"
    if not isinstance(config["font"], str):
        return False, "font must be a string"
    if not isinstance(config["heading_size"], int) or config["heading_size"] < 8 or config["heading_size"] > 24:
        return False, "heading_size must be an integer between 8 and 24"
    if not isinstance(config["body_size"], int) or config["body_size"] < 8 or config["body_size"] > 14:
        return False, "body_size must be an integer between 8 and 14"
    if not isinstance(config["line_spacing"], int) or config["line_spacing"] < 4 or config["line_spacing"] > 20:
        return False, "line_spacing must be an integer between 4 and 20"
    if not isinstance(config["section_spacing"], int) or config["section_spacing"] < 8 or config["section_spacing"] > 30:
        return False, "section_spacing must be an integer between 8 and 30"
    
    return True, None


def create_custom_template(base_template_id: str, customizations: dict) -> dict:
    """
    Create a custom template based on an existing template with customizations.
    
    Args:
        base_template_id: ID of base template to customize
        customizations: Dictionary of customizations to apply
    
    Returns:
        Custom template configuration
    """
    base_template = TEMPLATES.get(base_template_id)
    if not base_template:
        raise ValueError(f"Base template '{base_template_id}' not found")
    
    # Start with base template
    custom_template = base_template.copy()
    
    # Apply customizations (only allow valid fields)
    allowed_fields = ["font", "heading_size", "body_size", "line_spacing", "section_spacing", "accent", "color_scheme"]
    for field, value in customizations.items():
        if field in allowed_fields:
            custom_template[field] = value
    
    # Validate the custom template
    is_valid, error = validate_template_config(custom_template)
    if not is_valid:
        raise ValueError(f"Invalid template configuration: {error}")
    
    return custom_template
