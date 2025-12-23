# agents/resume_structured.py
"""
Helper functions for working with structured resume data.

Provides utilities to:
- Extract structured data from parsed resumes
- Enhance ATS scoring with structured data
- Combine structured and text-based analysis
"""
from typing import Dict, List, Optional, Any, Set
import logging

logger = logging.getLogger(__name__)


def extract_skills_from_structured(parsed_data: Dict[str, Any]) -> List[str]:
    """
    Extract skills from structured resume data.
    
    Args:
        parsed_data: Parsed resume data from resume_parser
    
    Returns:
        List of skills
    """
    skills = set()
    
    # Direct skills list
    if "skills" in parsed_data:
        for skill in parsed_data["skills"]:
            if skill and isinstance(skill, str):
                skills.add(skill.strip())
    
    # Extract from experience bullets
    for exp in parsed_data.get("experience", []):
        bullets = exp.get("bullets", [])
        for bullet in bullets:
            # Look for technical terms (basic heuristic)
            # This is a simple approach - could be enhanced with NLP
            if isinstance(bullet, str):
                # Common technical keywords
                tech_keywords = [
                    "python", "java", "javascript", "react", "node", "sql",
                    "aws", "docker", "kubernetes", "git", "api", "rest",
                    "microservices", "agile", "scrum", "ci/cd", "devops"
                ]
                bullet_lower = bullet.lower()
                for keyword in tech_keywords:
                    if keyword in bullet_lower:
                        skills.add(keyword)
    
    # Extract from projects
    for project in parsed_data.get("projects", []):
        technologies = project.get("technologies", [])
        for tech in technologies:
            if tech and isinstance(tech, str):
                skills.add(tech.strip())
    
    return list(skills)


def extract_companies_from_structured(parsed_data: Dict[str, Any]) -> List[str]:
    """
    Extract company names from structured resume data.
    
    Args:
        parsed_data: Parsed resume data
    
    Returns:
        List of company names
    """
    companies = []
    for exp in parsed_data.get("experience", []):
        company = exp.get("company")
        if company and isinstance(company, str):
            companies.append(company.strip())
    return companies


def extract_job_titles_from_structured(parsed_data: Dict[str, Any]) -> List[str]:
    """
    Extract job titles from structured resume data.
    
    Args:
        parsed_data: Parsed resume data
    
    Returns:
        List of job titles
    """
    titles = []
    for exp in parsed_data.get("experience", []):
        title = exp.get("title")
        if title and isinstance(title, str):
            titles.append(title.strip())
    return titles


def extract_education_degrees_from_structured(parsed_data: Dict[str, Any]) -> List[str]:
    """
    Extract degrees from structured resume data.
    
    Args:
        parsed_data: Parsed resume data
    
    Returns:
        List of degrees
    """
    degrees = []
    for edu in parsed_data.get("education", []):
        degree = edu.get("degree")
        field = edu.get("field_of_study")
        if degree and isinstance(degree, str):
            degrees.append(degree.strip())
        if field and isinstance(field, str):
            degrees.append(field.strip())
    return degrees


def extract_certifications_from_structured(parsed_data: Dict[str, Any]) -> List[str]:
    """
    Extract certifications from structured resume data.
    
    Args:
        parsed_data: Parsed resume data
    
    Returns:
        List of certification names
    """
    certs = []
    for cert in parsed_data.get("certifications", []):
        name = cert.get("name")
        if name and isinstance(name, str):
            certs.append(name.strip())
    return certs


def extract_years_of_experience(parsed_data: Dict[str, Any]) -> Optional[float]:
    """
    Calculate years of experience from structured resume data.
    
    Args:
        parsed_data: Parsed resume data
    
    Returns:
        Years of experience as float, or None if cannot calculate
    """
    from datetime import datetime
    import re
    
    total_months = 0
    
    for exp in parsed_data.get("experience", []):
        start_date = exp.get("start_date")
        end_date = exp.get("end_date") or exp.get("end_date")
        is_current = exp.get("is_current", False)
        
        if not start_date:
            continue
        
        # Parse start date
        start_year = _extract_year_from_date(start_date)
        if not start_year:
            continue
        
        # Parse end date
        if is_current or end_date in ["Present", "Current", "Now"]:
            end_year = datetime.now().year
        else:
            end_year = _extract_year_from_date(end_date) if end_date else None
        
        if end_year and start_year:
            years = end_year - start_year
            # Estimate months (assume 6 months if only year given)
            if years == 0:
                total_months += 6  # Assume 6 months for same-year positions
            else:
                total_months += years * 12
    
    if total_months > 0:
        return round(total_months / 12, 1)
    
    return None


def _extract_year_from_date(date_str: str) -> Optional[int]:
    """Extract year from date string."""
    import re
    
    if not date_str:
        return None
    
    # Try to find 4-digit year
    match = re.search(r'\b(19|20)\d{2}\b', str(date_str))
    if match:
        return int(match.group())
    
    return None


def create_enhanced_resume_text(parsed_data: Dict[str, Any], original_text: str) -> str:
    """
    Create enhanced resume text by combining structured data with original text.
    
    This helps ATS scoring by ensuring structured information is present in text.
    
    Args:
        parsed_data: Parsed resume data
        original_text: Original resume text
    
    Returns:
        Enhanced resume text
    """
    enhanced_parts = []
    
    # Add structured skills explicitly
    skills = extract_skills_from_structured(parsed_data)
    if skills:
        enhanced_parts.append(f"Skills: {', '.join(skills)}")
    
    # Add structured experience summaries
    for exp in parsed_data.get("experience", []):
        company = exp.get("company", "")
        title = exp.get("title", "")
        if company and title:
            enhanced_parts.append(f"{title} at {company}")
    
    # Add education
    for edu in parsed_data.get("education", []):
        institution = edu.get("institution", "")
        degree = edu.get("degree", "")
        field = edu.get("field_of_study", "")
        if institution:
            edu_str = f"{degree} in {field} from {institution}" if degree and field else f"{degree} from {institution}" if degree else institution
            enhanced_parts.append(edu_str)
    
    # Add certifications
    certs = extract_certifications_from_structured(parsed_data)
    if certs:
        enhanced_parts.append(f"Certifications: {', '.join(certs)}")
    
    # Combine with original text
    if enhanced_parts:
        enhanced_text = original_text + "\n\n" + "\n".join(enhanced_parts)
        return enhanced_text
    
    return original_text


def get_resume_summary_from_structured(parsed_data: Dict[str, Any]) -> Optional[str]:
    """
    Get resume summary from structured data.
    
    Args:
        parsed_data: Parsed resume data
    
    Returns:
        Summary text or None
    """
    return parsed_data.get("summary")


def get_contact_info_from_structured(parsed_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get contact information from structured data.
    
    Args:
        parsed_data: Parsed resume data
    
    Returns:
        Contact information dictionary
    """
    return parsed_data.get("contact", {})


def validate_parsed_data_completeness(parsed_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and score completeness of parsed resume data.
    
    Args:
        parsed_data: Parsed resume data
    
    Returns:
        Dictionary with completeness scores and missing fields
    """
    scores = {
        "contact": 0,
        "experience": 0,
        "education": 0,
        "skills": 0,
        "overall": 0,
    }
    
    missing_fields = []
    
    # Check contact info
    contact = parsed_data.get("contact", {})
    contact_fields = ["name", "email", "phone", "location"]
    contact_score = sum(1 for field in contact_fields if contact.get(field))
    scores["contact"] = contact_score / len(contact_fields)
    if contact_score < len(contact_fields):
        missing_fields.extend([f for f in contact_fields if not contact.get(f)])
    
    # Check experience
    experience = parsed_data.get("experience", [])
    if experience:
        scores["experience"] = 1.0
        # Check if experience entries have required fields
        complete_experiences = sum(
            1 for exp in experience
            if exp.get("company") and exp.get("title")
        )
        if complete_experiences < len(experience):
            missing_fields.append("Some experience entries missing company or title")
    else:
        missing_fields.append("No work experience found")
    
    # Check education
    education = parsed_data.get("education", [])
    if education:
        scores["education"] = 1.0
        complete_education = sum(
            1 for edu in education
            if edu.get("institution") and edu.get("degree")
        )
        if complete_education < len(education):
            missing_fields.append("Some education entries missing institution or degree")
    else:
        missing_fields.append("No education found")
    
    # Check skills
    skills = parsed_data.get("skills", [])
    if skills:
        scores["skills"] = min(1.0, len(skills) / 10)  # Normalize to 1.0 if 10+ skills
    else:
        missing_fields.append("No skills found")
    
    # Overall score
    scores["overall"] = sum(scores.values()) / len([k for k in scores.keys() if k != "overall"])
    
    return {
        "scores": scores,
        "missing_fields": missing_fields,
        "completeness_percentage": round(scores["overall"] * 100, 1),
    }

