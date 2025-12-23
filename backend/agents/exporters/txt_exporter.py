def export_txt(resume: dict) -> str:
    lines = []

    if resume.get("summary"):
        lines.append(resume["summary"])
        lines.append("")

    for exp in resume.get("experience", []):
        lines.append(exp["title"])
        for b in exp.get("bullets", []):
            lines.append(f"- {b}")
        lines.append("")

    if resume.get("skills"):
        lines.append("Skills:")
        lines.append(", ".join(resume["skills"]))

    return "\n".join(lines)
