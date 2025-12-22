from io import BytesIO
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib.enums import TA_LEFT

from agents.templates.registry import TEMPLATES


def render_pdf(resume_sections: dict, template_id: str) -> BytesIO:
    if template_id not in TEMPLATES:
        raise ValueError("Invalid template")

    t = TEMPLATES[template_id]
    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = {
        "heading": ParagraphStyle(
            "Heading",
            fontName=t["font"],
            fontSize=t["heading_size"],
            spaceAfter=t["line_spacing"],
            alignment=TA_LEFT,
        ),
        "body": ParagraphStyle(
            "Body",
            fontName="Helvetica",
            fontSize=t["body_size"],
            spaceAfter=t["line_spacing"],
            alignment=TA_LEFT,
        ),
    }

    story = []

    # Summary
    if resume_sections["summary"]:
        story.append(Paragraph("SUMMARY", styles["heading"]))
        story.append(Paragraph(resume_sections["summary"], styles["body"]))
        story.append(Spacer(1, t["section_spacing"]))

    # Experience
    if resume_sections["experience"]:
        story.append(Paragraph("EXPERIENCE", styles["heading"]))

        for exp in resume_sections["experience"]:
            story.append(
                Paragraph(exp.get("title", ""), styles["body"])
            )
            for bullet in exp.get("bullets", []):
                story.append(
                    Paragraph(f"- {bullet}", styles["body"])
                )
            story.append(Spacer(1, t["line_spacing"]))

        story.append(Spacer(1, t["section_spacing"]))

    # Skills
    if resume_sections["skills"]:
        story.append(Paragraph("SKILLS", styles["heading"]))
        story.append(
            Paragraph(
                ", ".join(resume_sections["skills"]),
                styles["body"],
            )
        )

    doc.build(story)
    buffer.seek(0)
    return buffer
