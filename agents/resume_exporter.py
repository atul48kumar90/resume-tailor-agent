from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4



def format_resume_text(rewritten: dict) -> str:
    """
    Converts rewritten resume JSON into clean human-readable text.
    """
    lines = []

    if rewritten.get("summary"):
        lines.append("SUMMARY")
        lines.append(rewritten["summary"])
        lines.append("")

    for exp in rewritten.get("experience", []):
        if exp.get("title"):
            lines.append(exp["title"])
        for bullet in exp.get("bullets", []):
            lines.append(f"- {bullet}")
        lines.append("")

    if rewritten.get("skills"):
        lines.append("SKILLS")
        lines.append(", ".join(rewritten["skills"]))

    return "\n".join(lines).strip()


def export_pdf(resume_text: str) -> BytesIO:
    """
    Generates a clean, ATS-safe PDF resume.
    """
    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()
    normal = styles["Normal"]

    story = []

    for line in resume_text.split("\n"):
        if not line.strip():
            story.append(Spacer(1, 8))
        else:
            story.append(Paragraph(line, normal))

    doc.build(story)
    buffer.seek(0)
    return buffer
