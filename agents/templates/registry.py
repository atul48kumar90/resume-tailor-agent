from typing import Dict

TEMPLATES: Dict[str, dict] = {
    "classic": {
        "name": "Classic ATS",
        "font": "Helvetica",
        "heading_size": 14,
        "body_size": 10,
        "line_spacing": 8,
        "section_spacing": 14,
        "accent": False,
    },
    "modern": {
        "name": "Modern Clean",
        "font": "Helvetica-Bold",
        "heading_size": 15,
        "body_size": 10,
        "line_spacing": 9,
        "section_spacing": 16,
        "accent": True,
    },
    "compact": {
        "name": "Compact One-Page",
        "font": "Helvetica",
        "heading_size": 13,
        "body_size": 9,
        "line_spacing": 6,
        "section_spacing": 10,
        "accent": False,
    },
}
