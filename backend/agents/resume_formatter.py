def format_resume_text(rewritten: dict) -> str:
    """
    Converts rewritten resume JSON into clean human-readable text.
    Preserves all sections: contact, summary, experience, education, skills, etc.
    """
    lines = []

    # Contact Information
    contact = rewritten.get("contact", {})
    if contact:
        if contact.get("name"):
            lines.append(contact["name"].upper())
        contact_parts = []
        if contact.get("email"):
            contact_parts.append(contact["email"])
        if contact.get("phone"):
            contact_parts.append(contact["phone"])
        if contact.get("location"):
            contact_parts.append(contact["location"])
        if contact.get("linkedin"):
            contact_parts.append(contact["linkedin"])
        if contact_parts:
            lines.append(" • ".join(contact_parts))
        lines.append("")

    # Summary
    if rewritten.get("summary"):
        lines.append("SUMMARY")
        lines.append(rewritten["summary"])
        lines.append("")

    # Experience
    experience = rewritten.get("experience", [])
    if experience:
        lines.append("EXPERIENCE")
        for exp in experience:
            # Format: "Company, Title" or just "Title"
            title_parts = []
            if exp.get("company"):
                title_parts.append(exp["company"])
            if exp.get("title"):
                title_parts.append(exp["title"])
            if title_parts:
                lines.append(", ".join(title_parts))
            
            # Add date range if available
            date_parts = []
            if exp.get("start_date"):
                date_parts.append(exp["start_date"])
            if exp.get("end_date"):
                date_parts.append(exp["end_date"])
            if date_parts:
                lines.append(" - ".join(date_parts))
            
            # Add bullets
            for bullet in exp.get("bullets", []):
                lines.append(f"- {bullet}")
            lines.append("")

    # Education
    education = rewritten.get("education", [])
    if education:
        lines.append("EDUCATION")
        for edu in education:
            edu_parts = []
            if edu.get("institution"):
                edu_parts.append(edu["institution"])
            if edu.get("degree"):
                edu_parts.append(edu["degree"])
            if edu.get("field_of_study"):
                edu_parts.append(f"in {edu['field_of_study']}")
            if edu_parts:
                lines.append(", ".join(edu_parts))
            
            # Add date range if available
            edu_date_parts = []
            if edu.get("start_date"):
                edu_date_parts.append(edu["start_date"])
            if edu.get("end_date"):
                edu_date_parts.append(edu["end_date"])
            if edu_date_parts:
                lines.append(" - ".join(edu_date_parts))
            
            if edu.get("gpa"):
                lines.append(f"GPA: {edu['gpa']}")
            lines.append("")

    # Skills
    skills = rewritten.get("skills", [])
    if skills:
        lines.append("SKILLS")
        lines.append(", ".join(skills))
        lines.append("")

    # Certifications
    certifications = rewritten.get("certifications", [])
    if certifications:
        lines.append("CERTIFICATIONS")
        for cert in certifications:
            cert_parts = []
            if cert.get("name"):
                cert_parts.append(cert["name"])
            if cert.get("issuer"):
                cert_parts.append(f"({cert['issuer']})")
            if cert_parts:
                lines.append(" • ".join(cert_parts))
            if cert.get("date"):
                lines.append(f"Date: {cert['date']}")
        lines.append("")

    # Projects
    projects = rewritten.get("projects", [])
    if projects:
        lines.append("PROJECTS")
        for project in projects:
            if project.get("name"):
                lines.append(project["name"])
            if project.get("description"):
                lines.append(project["description"])
            if project.get("technologies"):
                lines.append(f"Technologies: {', '.join(project['technologies'])}")
            lines.append("")

    return "\n".join(lines).strip()


def format_resume_sections(resume: dict) -> dict:
    """
    Converts resume JSON into logical sections.
    Template renderer decides how to display.
    
    Supports all sections from parsed resume data:
    - contact: Contact information
    - summary: Professional summary
    - experience: Work experience
    - education: Education entries
    - skills: Skills list
    - certifications: Certifications
    - projects: Projects
    """
    return {
        "contact": resume.get("contact", {}),
        "summary": resume.get("summary", ""),
        "experience": resume.get("experience", []),
        "education": resume.get("education", []),
        "skills": resume.get("skills", []),
        "certifications": resume.get("certifications", []),
        "projects": resume.get("projects", []),
        "languages": resume.get("languages", []),
        "awards": resume.get("awards", []),
    }
