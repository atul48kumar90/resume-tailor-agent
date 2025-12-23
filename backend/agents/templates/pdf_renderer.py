from io import BytesIO
from typing import Optional, Dict, Any
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib import colors
from reportlab.lib.units import inch

from agents.templates.registry import TEMPLATES, get_template


def render_pdf(
    resume_sections: dict,
    template_id: str = "classic",
    custom_template: Optional[Dict[str, Any]] = None
) -> BytesIO:
    """
    Render resume as PDF using specified template.
    
    Args:
        resume_sections: Dictionary with resume sections (summary, experience, skills, etc.)
        template_id: Template ID from registry
        custom_template: Optional custom template configuration (overrides template_id)
    
    Returns:
        BytesIO buffer with PDF content
    """
    # Use custom template if provided, otherwise get from registry
    if custom_template:
        t = custom_template
    else:
        t = get_template(template_id)
        if not t:
            raise ValueError(f"Invalid template ID: {template_id}")
    
    buffer = BytesIO()

    # Set margins based on layout
    margins = 36 if t.get("layout") == "single-column" else 30
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=margins,
        leftMargin=margins,
        topMargin=margins,
        bottomMargin=margins,
    )

    # Define color scheme
    color_scheme = t.get("color_scheme", "monochrome")
    accent_color = _get_accent_color(color_scheme, t.get("accent", False))

    # Create styles
    styles = _create_styles(t, accent_color)

    story = []

    # Contact information (if available in resume_sections)
    if "contact" in resume_sections and resume_sections["contact"]:
        contact = resume_sections["contact"]
        contact_text = []
        if contact.get("name"):
            contact_text.append(contact["name"])
        if contact.get("email"):
            contact_text.append(contact["email"])
        if contact.get("phone"):
            contact_text.append(contact["phone"])
        if contact.get("location"):
            contact_text.append(contact["location"])
        
        if contact_text:
            story.append(Paragraph(" | ".join(contact_text), styles["contact"]))
            story.append(Spacer(1, t["section_spacing"]))

    # Summary
    if resume_sections.get("summary"):
        story.append(Paragraph("SUMMARY", styles["heading"]))
        story.append(Paragraph(resume_sections["summary"], styles["body"]))
        story.append(Spacer(1, t["section_spacing"]))

    # Experience
    if resume_sections.get("experience"):
        story.append(Paragraph("EXPERIENCE", styles["heading"]))

        for exp in resume_sections["experience"]:
            # Company and title
            title_text = exp.get("title", "")
            company = exp.get("company", "")
            if company:
                title_text += f" | {company}"
            
            dates = ""
            if exp.get("start_date") or exp.get("end_date"):
                start = exp.get("start_date", "")
                end = exp.get("end_date", "Present")
                dates = f" ({start} - {end})"
            
            story.append(Paragraph(title_text + dates, styles["subheading"]))
            
            # Bullets
            for bullet in exp.get("bullets", []):
                story.append(Paragraph(f"• {bullet}", styles["body"]))
            
            story.append(Spacer(1, t["line_spacing"]))

        story.append(Spacer(1, t["section_spacing"]))

    # Education
    if resume_sections.get("education"):
        story.append(Paragraph("EDUCATION", styles["heading"]))
        for edu in resume_sections["education"]:
            edu_text = []
            if edu.get("degree"):
                edu_text.append(edu["degree"])
            if edu.get("field_of_study"):
                edu_text.append(edu["field_of_study"])
            if edu.get("institution"):
                edu_text.append(f" - {edu['institution']}")
            
            if edu_text:
                story.append(Paragraph("".join(edu_text), styles["body"]))
        
        story.append(Spacer(1, t["section_spacing"]))

    # Skills
    if resume_sections.get("skills"):
        story.append(Paragraph("SKILLS", styles["heading"]))
        
        # For two-column layout, use table for skills
        if t.get("layout") == "two-column" and len(resume_sections["skills"]) > 5:
            skills_text = ", ".join(resume_sections["skills"])
            story.append(Paragraph(skills_text, styles["body"]))
        else:
            skills_text = ", ".join(resume_sections["skills"])
            story.append(Paragraph(skills_text, styles["body"]))

    # Certifications
    if resume_sections.get("certifications"):
        story.append(Paragraph("CERTIFICATIONS", styles["heading"]))
        for cert in resume_sections["certifications"]:
            cert_text = cert.get("name", "")
            if cert.get("issuer"):
                cert_text += f" - {cert['issuer']}"
            if cert.get("date"):
                cert_text += f" ({cert['date']})"
            story.append(Paragraph(cert_text, styles["body"]))
        story.append(Spacer(1, t["section_spacing"]))

    # Projects
    if resume_sections.get("projects"):
        story.append(Paragraph("PROJECTS", styles["heading"]))
        for project in resume_sections["projects"]:
            project_text = project.get("name", "")
            if project.get("description"):
                project_text += f": {project['description']}"
            story.append(Paragraph(project_text, styles["body"]))
        story.append(Spacer(1, t["section_spacing"]))

    doc.build(story)
    buffer.seek(0)
    return buffer


def _get_accent_color(color_scheme: str, has_accent: bool) -> Optional[colors.Color]:
    """Get accent color based on color scheme."""
    if not has_accent:
        return None
    
    color_map = {
        "blue": colors.HexColor("#0066CC"),
        "green": colors.HexColor("#006600"),
        "professional": colors.HexColor("#333333"),
        "monochrome": colors.HexColor("#000000"),
    }
    
    return color_map.get(color_scheme, colors.HexColor("#0066CC"))


def _create_styles(template: dict, accent_color: Optional[colors.Color]) -> dict:
    """Create paragraph styles for the template."""
    styles = {
        "heading": ParagraphStyle(
            "Heading",
            fontName=template["font"],
            fontSize=template["heading_size"],
            spaceAfter=template["line_spacing"],
            alignment=TA_LEFT,
            textColor=accent_color if accent_color else colors.black,
            fontStyle="Bold" if "Bold" in template["font"] else "Normal",
        ),
        "subheading": ParagraphStyle(
            "Subheading",
            fontName="Helvetica-Bold",
            fontSize=template["body_size"] + 1,
            spaceAfter=template["line_spacing"] // 2,
            alignment=TA_LEFT,
        ),
        "body": ParagraphStyle(
            "Body",
            fontName="Helvetica",
            fontSize=template["body_size"],
            spaceAfter=template["line_spacing"],
            alignment=TA_LEFT,
        ),
        "contact": ParagraphStyle(
            "Contact",
            fontName="Helvetica-Bold",
            fontSize=template["heading_size"],
            spaceAfter=template["line_spacing"],
            alignment=TA_CENTER,
            textColor=accent_color if accent_color else colors.black,
        ),
    }
    
    return styles
