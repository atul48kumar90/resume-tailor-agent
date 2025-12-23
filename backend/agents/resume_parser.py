# agents/resume_parser.py
"""
Intelligent Resume Parser

Extracts structured information from resume text:
- Contact information (name, email, phone, address, LinkedIn, etc.)
- Education (institutions, degrees, dates, GPA, etc.)
- Work experience (companies, titles, dates, locations, descriptions)
- Certifications
- Skills
- Projects
- Languages
- Awards and achievements
"""
import json
import re
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from core.llm_safe_async import safe_llm_call_async
from core.cache_async import get_cached_resume_parse, set_cached_resume_parse

logger = logging.getLogger(__name__)


# ============================================================
# Pydantic Models for Structured Resume Data
# ============================================================

class ContactInfo:
    """Contact information extracted from resume."""
    def __init__(self, data: Dict[str, Any]):
        self.name: Optional[str] = data.get("name")
        self.email: Optional[str] = data.get("email")
        self.phone: Optional[str] = data.get("phone")
        self.address: Optional[str] = data.get("address")
        self.linkedin: Optional[str] = data.get("linkedin")
        self.github: Optional[str] = data.get("github")
        self.website: Optional[str] = data.get("website")
        self.location: Optional[str] = data.get("location")
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "address": self.address,
            "linkedin": self.linkedin,
            "github": self.github,
            "website": self.website,
            "location": self.location,
        }


class EducationEntry:
    """Education entry extracted from resume."""
    def __init__(self, data: Dict[str, Any]):
        self.institution: Optional[str] = data.get("institution")
        self.degree: Optional[str] = data.get("degree")
        self.field_of_study: Optional[str] = data.get("field_of_study")
        self.start_date: Optional[str] = data.get("start_date")
        self.end_date: Optional[str] = data.get("end_date")
        self.gpa: Optional[str] = data.get("gpa")
        self.honors: Optional[str] = data.get("honors")
        self.location: Optional[str] = data.get("location")
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "institution": self.institution,
            "degree": self.degree,
            "field_of_study": self.field_of_study,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "gpa": self.gpa,
            "honors": self.honors,
            "location": self.location,
        }


class WorkExperience:
    """Work experience entry extracted from resume."""
    def __init__(self, data: Dict[str, Any]):
        self.company: Optional[str] = data.get("company")
        self.title: Optional[str] = data.get("title")
        self.start_date: Optional[str] = data.get("start_date")
        self.end_date: Optional[str] = data.get("end_date")
        self.location: Optional[str] = data.get("location")
        self.description: Optional[str] = data.get("description")
        self.bullets: List[str] = data.get("bullets", [])
        self.is_current: bool = data.get("is_current", False)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "company": self.company,
            "title": self.title,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "location": self.location,
            "description": self.description,
            "bullets": self.bullets,
            "is_current": self.is_current,
        }


class Certification:
    """Certification entry extracted from resume."""
    def __init__(self, data: Dict[str, Any]):
        self.name: Optional[str] = data.get("name")
        self.issuer: Optional[str] = data.get("issuer")
        self.date: Optional[str] = data.get("date")
        self.expiration_date: Optional[str] = data.get("expiration_date")
        self.credential_id: Optional[str] = data.get("credential_id")
        self.url: Optional[str] = data.get("url")
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "issuer": self.issuer,
            "date": self.date,
            "expiration_date": self.expiration_date,
            "credential_id": self.credential_id,
            "url": self.url,
        }


class Project:
    """Project entry extracted from resume."""
    def __init__(self, data: Dict[str, Any]):
        self.name: Optional[str] = data.get("name")
        self.description: Optional[str] = data.get("description")
        self.technologies: List[str] = data.get("technologies", [])
        self.url: Optional[str] = data.get("url")
        self.start_date: Optional[str] = data.get("start_date")
        self.end_date: Optional[str] = data.get("end_date")
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "technologies": self.technologies,
            "url": self.url,
            "start_date": self.start_date,
            "end_date": self.end_date,
        }


# ============================================================
# LLM-Based Parsing
# ============================================================

RESUME_PARSE_PROMPT = """
You are an expert resume parser. Extract structured information from the resume text below.

HARD CONSTRAINTS:
- ONLY extract information that is EXPLICITLY stated in the resume text
- DO NOT infer, assume, or make up any information
- DO NOT add skills, experiences, or qualifications that are not mentioned
- If a field is not present in the resume, set it to null (not empty string)
- Dates must be in the exact format found in the resume (e.g., "Jan 2020", "2020-2023", "Present")
- Company names, job titles, and institution names must match exactly as written

You MUST output a valid JSON object with the following structure:
{{
    "contact": {{
        "name": "Full name if explicitly stated, else null",
        "email": "Email address if found, else null",
        "phone": "Phone number if found, else null",
        "address": "Full address if found, else null",
        "linkedin": "LinkedIn URL if found, else null",
        "github": "GitHub URL if found, else null",
        "website": "Personal website if found, else null",
        "location": "City, State/Country if found, else null"
    }},
    "education": [
        {{
            "institution": "University/College name",
            "degree": "Degree type (e.g., Bachelor's, Master's, PhD)",
            "field_of_study": "Major/Field of study",
            "start_date": "Start date as written in resume",
            "end_date": "End date or 'Present' if ongoing",
            "gpa": "GPA if mentioned, else null",
            "honors": "Honors/awards if mentioned, else null",
            "location": "Location if mentioned, else null"
        }}
    ],
    "experience": [
        {{
            "company": "Company name exactly as written",
            "title": "Job title exactly as written",
            "start_date": "Start date as written",
            "end_date": "End date or 'Present' if current",
            "location": "Location if mentioned, else null",
            "description": "Brief description if provided",
            "bullets": ["Bullet point 1", "Bullet point 2", ...],
            "is_current": true/false
        }}
    ],
    "certifications": [
        {{
            "name": "Certification name",
            "issuer": "Issuing organization",
            "date": "Date obtained",
            "expiration_date": "Expiration date if mentioned, else null",
            "credential_id": "Credential ID if mentioned, else null",
            "url": "URL if mentioned, else null"
        }}
    ],
    "projects": [
        {{
            "name": "Project name",
            "description": "Project description",
            "technologies": ["Tech 1", "Tech 2", ...],
            "url": "Project URL if mentioned, else null",
            "start_date": "Start date if mentioned, else null",
            "end_date": "End date if mentioned, else null"
        }}
    ],
    "skills": ["Skill 1", "Skill 2", ...],
    "languages": ["Language 1 (proficiency)", "Language 2 (proficiency)", ...],
    "awards": ["Award 1", "Award 2", ...],
    "summary": "Professional summary/objective if present, else null"
}}

Resume text:
{resume_text}

Extract ONLY the information explicitly stated. Output a valid JSON object matching the structure above. Use null for missing fields, not empty strings or omitted fields.
"""


def _validate_parsed_resume(response: str) -> bool:
    """Validate that the parsed resume response is valid JSON and contains expected structure."""
    if not response or not response.strip():
        logger.warning("Empty response from LLM")
        return False
    
    # Clean response: remove markdown code blocks if present
    cleaned_response = response.strip()
    
    # Remove markdown code blocks (```json ... ``` or ``` ... ```)
    if cleaned_response.startswith("```"):
        # Find the first newline after ```
        first_newline = cleaned_response.find("\n")
        if first_newline != -1:
            cleaned_response = cleaned_response[first_newline + 1:]
        # Remove trailing ```
        if cleaned_response.endswith("```"):
            cleaned_response = cleaned_response[:-3]
        cleaned_response = cleaned_response.strip()
    
    # Try to extract JSON if there's text before/after
    # Look for first { and last }
    first_brace = cleaned_response.find("{")
    last_brace = cleaned_response.rfind("}")
    
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        cleaned_response = cleaned_response[first_brace:last_brace + 1]
    
    try:
        data = json.loads(cleaned_response)
        
        # Check that it's a dictionary
        if not isinstance(data, dict):
            logger.warning(f"Response is not a dictionary: {type(data)}")
            return False
        
        # Check for required top-level keys
        required_keys = ["contact", "education", "experience", "skills"]
        missing_keys = [key for key in required_keys if key not in data]
        if missing_keys:
            logger.warning(f"Missing required keys: {missing_keys}")
            return False
        
        # Validate contact is a dict
        if not isinstance(data.get("contact"), dict):
            logger.warning(f"Contact is not a dict: {type(data.get('contact'))}")
            return False
        
        # Validate education is a list
        if not isinstance(data.get("education"), list):
            logger.warning(f"Education is not a list: {type(data.get('education'))}")
            return False
        
        # Validate experience is a list
        if not isinstance(data.get("experience"), list):
            logger.warning(f"Experience is not a list: {type(data.get('experience'))}")
            return False
        
        # Validate skills is a list
        if not isinstance(data.get("skills"), list):
            logger.warning(f"Skills is not a list: {type(data.get('skills'))}")
            return False
        
        return True
        
    except json.JSONDecodeError as e:
        logger.warning(f"JSON decode error: {e}. Response preview: {response[:200]}...")
        return False
    except (KeyError, TypeError) as e:
        logger.warning(f"Validation error: {e}")
        return False


def _validate_grounded_in_source(parsed_data: Dict[str, Any], resume_text: str) -> Dict[str, Any]:
    """
    Validate that parsed data is grounded in the source resume text.
    Remove any fields that cannot be verified.
    """
    resume_lower = resume_text.lower()
    validated_data = {
        "contact": {},
        "education": [],
        "experience": [],
        "certifications": [],
        "projects": [],
        "skills": [],
        "languages": [],
        "awards": [],
        "summary": None,
    }
    
    # Validate contact info
    contact = parsed_data.get("contact", {})
    for key, value in contact.items():
        if value and isinstance(value, str):
            # Check if value appears in resume (case-insensitive)
            if value.lower() in resume_lower or _fuzzy_match_in_text(value, resume_text):
                validated_data["contact"][key] = value
    
    # Validate education
    for edu in parsed_data.get("education", []):
        if _validate_education_entry(edu, resume_text):
            validated_data["education"].append(edu)
    
    # Validate experience
    for exp in parsed_data.get("experience", []):
        if _validate_experience_entry(exp, resume_text):
            validated_data["experience"].append(exp)
    
    # Validate certifications
    for cert in parsed_data.get("certifications", []):
        if _validate_certification_entry(cert, resume_text):
            validated_data["certifications"].append(cert)
    
    # Validate projects
    for proj in parsed_data.get("projects", []):
        if _validate_project_entry(proj, resume_text):
            validated_data["projects"].append(proj)
    
    # Validate skills (must appear in resume)
    for skill in parsed_data.get("skills", []):
        if skill and isinstance(skill, str):
            if skill.lower() in resume_lower or _fuzzy_match_in_text(skill, resume_text):
                validated_data["skills"].append(skill)
    
    # Validate languages
    for lang in parsed_data.get("languages", []):
        if lang and isinstance(lang, str):
            if lang.lower() in resume_lower or _fuzzy_match_in_text(lang, resume_text):
                validated_data["languages"].append(lang)
    
    # Validate awards
    for award in parsed_data.get("awards", []):
        if award and isinstance(award, str):
            if award.lower() in resume_lower or _fuzzy_match_in_text(award, resume_text):
                validated_data["awards"].append(award)
    
    # Validate summary (must be grounded in resume)
    summary = parsed_data.get("summary")
    if summary and isinstance(summary, str):
        # Check if summary contains phrases from resume
        if _validate_summary(summary, resume_text):
            validated_data["summary"] = summary
    
    return validated_data


def _fuzzy_match_in_text(value: str, text: str) -> bool:
    """Check if value appears in text with fuzzy matching (handles variations)."""
    import difflib
    value_lower = value.lower()
    text_lower = text.lower()
    
    # Check exact match
    if value_lower in text_lower:
        return True
    
    # Check fuzzy match (similarity > 0.8)
    words = value_lower.split()
    if len(words) > 0:
        for i in range(len(text_lower) - len(value_lower) + 1):
            substring = text_lower[i:i+len(value_lower)]
            similarity = difflib.SequenceMatcher(None, value_lower, substring).ratio()
            if similarity > 0.8:
                return True
    
    return False


def _validate_education_entry(edu: Dict[str, Any], resume_text: str) -> bool:
    """Validate that education entry is grounded in resume text."""
    institution = edu.get("institution", "")
    degree = edu.get("degree", "")
    
    if not institution and not degree:
        return False
    
    resume_lower = resume_text.lower()
    
    # Check if institution or degree appears in resume
    if institution and institution.lower() in resume_lower:
        return True
    if degree and degree.lower() in resume_lower:
        return True
    
    return False


def _validate_experience_entry(exp: Dict[str, Any], resume_text: str) -> bool:
    """Validate that experience entry is grounded in resume text."""
    company = exp.get("company", "")
    title = exp.get("title", "")
    
    if not company and not title:
        return False
    
    resume_lower = resume_text.lower()
    
    # Check if company or title appears in resume
    if company and company.lower() in resume_lower:
        return True
    if title and title.lower() in resume_lower:
        return True
    
    return False


def _validate_certification_entry(cert: Dict[str, Any], resume_text: str) -> bool:
    """Validate that certification entry is grounded in resume text."""
    name = cert.get("name", "")
    
    if not name:
        return False
    
    resume_lower = resume_text.lower()
    return name.lower() in resume_lower or _fuzzy_match_in_text(name, resume_text)


def _validate_project_entry(proj: Dict[str, Any], resume_text: str) -> bool:
    """Validate that project entry is grounded in resume text."""
    name = proj.get("name", "")
    
    if not name:
        return False
    
    resume_lower = resume_text.lower()
    return name.lower() in resume_lower or _fuzzy_match_in_text(name, resume_text)


def _validate_summary(summary: str, resume_text: str) -> bool:
    """Validate that summary is grounded in resume text."""
    # Check if summary contains key phrases from resume
    summary_words = set(summary.lower().split())
    resume_words = set(resume_text.lower().split())
    
    # At least 30% of summary words should appear in resume
    common_words = summary_words.intersection(resume_words)
    if len(summary_words) > 0:
        overlap = len(common_words) / len(summary_words)
        return overlap >= 0.3
    
    return False


# ============================================================
# Public API
# ============================================================

async def parse_resume_async(resume_text: str, use_cache: bool = True) -> Dict[str, Any]:
    """
    Parse resume text and extract structured information.
    
    Args:
        resume_text: Raw resume text
        use_cache: Whether to use cached results
    
    Returns:
        Dictionary with structured resume data:
        {
            "contact": {...},
            "education": [...],
            "experience": [...],
            "certifications": [...],
            "projects": [...],
            "skills": [...],
            "languages": [...],
            "awards": [...],
            "summary": "..."
        }
    """
    import hashlib
    
    # Check cache
    if use_cache:
        resume_hash = hashlib.sha256(resume_text.encode()).hexdigest()
        cached_result = await get_cached_resume_parse(resume_hash)
        if cached_result:
            logger.info(f"Resume parse cache hit (hash: {resume_hash[:8]}...)")
            return cached_result
    
    # Prepare prompt
    prompt = RESUME_PARSE_PROMPT.format(resume_text=resume_text)
    
    # Call LLM with validation
    raw_response = await safe_llm_call_async(
        prompt=prompt,
        validation_fn=_validate_parsed_resume,
        fallback_value='{"contact": {}, "education": [], "experience": [], "skills": []}',
        max_retries=3,
        use_fast_model=False,  # Use smart model for better parsing
    )
    
    # Clean response: remove markdown code blocks if present
    cleaned_response = raw_response.strip()
    
    # Remove markdown code blocks (```json ... ``` or ``` ... ```)
    if cleaned_response.startswith("```"):
        first_newline = cleaned_response.find("\n")
        if first_newline != -1:
            cleaned_response = cleaned_response[first_newline + 1:]
        if cleaned_response.endswith("```"):
            cleaned_response = cleaned_response[:-3]
        cleaned_response = cleaned_response.strip()
    
    # Extract JSON if embedded in text
    first_brace = cleaned_response.find("{")
    last_brace = cleaned_response.rfind("}")
    
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        cleaned_response = cleaned_response[first_brace:last_brace + 1]
    
    try:
        parsed_data = json.loads(cleaned_response)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response as JSON: {e}")
        logger.error(f"Response preview: {raw_response[:500]}...")
        parsed_data = {"contact": {}, "education": [], "experience": [], "skills": []}
    
    # Validate that parsed data is grounded in source
    validated_data = _validate_grounded_in_source(parsed_data, resume_text)
    
    # Cache result
    if use_cache:
        resume_hash = hashlib.sha256(resume_text.encode()).hexdigest()
        await set_cached_resume_parse(resume_hash, validated_data, ttl=86400)  # 24 hours
    
    logger.info(f"Parsed resume: {len(validated_data.get('experience', []))} experiences, "
                f"{len(validated_data.get('education', []))} education entries, "
                f"{len(validated_data.get('skills', []))} skills")
    
    return validated_data


def parse_resume(resume_text: str, use_cache: bool = True) -> Dict[str, Any]:
    """
    Synchronous wrapper for parse_resume_async.
    """
    import asyncio
    return asyncio.run(parse_resume_async(resume_text, use_cache))


# ============================================================
# Helper Functions
# ============================================================

def extract_dates_from_text(text: str) -> List[str]:
    """
    Extract date patterns from text.
    Returns list of date strings found.
    """
    # Common date patterns
    patterns = [
        r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}\b',
        r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',
        r'\b\d{4}\s*[-–]\s*\d{4}\b',
        r'\b\d{4}\s*[-–]\s*(Present|Current|Now)\b',
        r'\b\d{4}\b',
    ]
    
    dates = []
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        dates.extend(matches)
    
    return list(set(dates))  # Remove duplicates


def extract_email_from_text(text: str) -> Optional[str]:
    """Extract email address from text."""
    pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    matches = re.findall(pattern, text)
    return matches[0] if matches else None


def extract_phone_from_text(text: str) -> Optional[str]:
    """Extract phone number from text."""
    patterns = [
        r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
        r'\(\d{3}\)\s*\d{3}[-.]?\d{4}',
        r'\+\d{1,3}\s*\d{3}[-.]?\d{3}[-.]?\d{4}',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text)
        if matches:
            return matches[0]
    
    return None


def extract_urls_from_text(text: str) -> List[str]:
    """Extract URLs from text."""
    pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
    matches = re.findall(pattern, text)
    return matches

