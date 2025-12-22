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


def format_resume_sections(resume: dict) -> dict:
    """
    Converts resume JSON into logical sections.
    Template renderer decides how to display.
    """
    return {
        "summary": resume.get("summary", ""),
        "experience": resume.get("experience", []),
        "skills": resume.get("skills", []),
    }
