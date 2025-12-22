def export_txt(resume: dict) -> bytes:
    lines = []

    if resume.get("summary"):
        lines.append("SUMMARY")
        lines.append(resume["summary"])
        lines.append("")

    if resume.get("experience"):
        lines.append("EXPERIENCE")
        for exp in resume["experience"]:
            lines.append(exp.get("title", ""))
            for b in exp.get("bullets", []):
                lines.append(f"- {b}")
            lines.append("")

    if resume.get("skills"):
        lines.append("SKILLS")
        lines.append(", ".join(resume["skills"]))

    return "\n".join(lines).encode("utf-8")
