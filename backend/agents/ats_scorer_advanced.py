# agents/ats_scorer_advanced.py
"""
Advanced ATS Scorer - Enterprise-grade scoring algorithm
Combines multiple signals for superior accuracy:
- Keyword matching (exact, semantic, contextual)
- Keyword placement weighting (titles/headers get more weight)
- Experience depth and recency scoring
- Education and certification matching
- Skill proficiency detection
- Multi-factor composite scoring
"""
from typing import Dict, List, Optional, Set, Any, Tuple
from datetime import datetime
import re
import logging

logger = logging.getLogger(__name__)

# Import base matching functions
from agents.ats_scorer import (
    _tokenize,
    _match_keyword,
    _normalize,
    KEYWORD_ALIASES,
    COMPOSITE_SKILLS,
)


# =========================================================
# Keyword Placement Weights (Industry Standard)
# =========================================================
# Keywords in strategic locations get higher weight
PLACEMENT_WEIGHTS = {
    "title": 2.0,  # Job titles - highest weight
    "header": 1.8,  # Section headers (Skills, Experience, etc.)
    "summary": 1.5,  # Professional summary
    "bullet_first": 1.3,  # First bullet in experience entry
    "bullet": 1.0,  # Regular bullet points
    "skills_section": 1.2,  # Dedicated skills section
    "education": 0.8,  # Education section
    "other": 0.7,  # Other locations
}


def _detect_keyword_placement(
    keyword: str,
    resume_text: str,
    parsed_data: Optional[Dict[str, Any]] = None
) -> str:
    """
    Detect where a keyword appears in the resume.
    Returns placement type for weighting.
    """
    keyword_lower = keyword.lower()
    keyword_tokens = set(_tokenize(keyword, use_cache=False))
    
    # Check in job titles
    if parsed_data:
        for exp in parsed_data.get("experience", []):
            title = exp.get("title", "").lower()
            if keyword_lower in title or any(
                token in _tokenize(title, use_cache=False) 
                for token in keyword_tokens
            ):
                return "title"
    
    # Check in section headers (Skills, Experience, etc.)
    header_patterns = [
        r"(?i)^\s*(skills?|experience|work\s+experience|professional\s+experience)",
        r"(?i)^\s*(education|certification|projects?)",
    ]
    lines = resume_text.split("\n")
    for i, line in enumerate(lines[:20]):  # Check first 20 lines
        if any(re.search(pattern, line) for pattern in header_patterns):
            # Check if keyword appears near this header
            context = " ".join(lines[max(0, i-2):min(len(lines), i+5)])
            if keyword_lower in context.lower():
                return "header"
    
    # Check in summary section
    if parsed_data:
        summary = parsed_data.get("summary", "")
        if summary and keyword_lower in summary.lower():
            return "summary"
    
    # Check in skills section
    if parsed_data:
        skills = parsed_data.get("skills", [])
        for skill in skills:
            if isinstance(skill, str) and keyword_lower in skill.lower():
                return "skills_section"
    
    # Check in first bullet of experience
    if parsed_data:
        for exp in parsed_data.get("experience", []):
            bullets = exp.get("bullets", [])
            if bullets and len(bullets) > 0:
                first_bullet = bullets[0].lower()
                if keyword_lower in first_bullet:
                    return "bullet_first"
    
    # Check in regular bullets
    if parsed_data:
        for exp in parsed_data.get("experience", []):
            for bullet in exp.get("bullets", []):
                if keyword_lower in bullet.lower():
                    return "bullet"
    
    # Check in education
    if parsed_data:
        for edu in parsed_data.get("education", []):
            edu_text = " ".join([
                edu.get("degree", ""),
                edu.get("field_of_study", ""),
                edu.get("institution", "")
            ]).lower()
            if keyword_lower in edu_text:
                return "education"
    
    return "other"


# =========================================================
# Experience Depth Scoring
# =========================================================

def _calculate_experience_score(
    parsed_data: Optional[Dict[str, Any]],
    jd_seniority: Optional[str] = None
) -> float:
    """
    Calculate experience depth score based on years of experience
    and match with JD seniority requirements.
    
    Returns score from 0.0 to 1.0
    """
    if not parsed_data:
        return 0.5  # Neutral if no data
    
    from agents.resume_structured import extract_years_of_experience
    
    years_exp = extract_years_of_experience(parsed_data)
    if not years_exp:
        return 0.5
    
    # Seniority level mapping
    seniority_requirements = {
        "entry": (0, 2),
        "junior": (0, 3),
        "mid": (2, 5),
        "senior": (5, 10),
        "lead": (7, 15),
        "principal": (10, 20),
        "staff": (8, 20),
    }
    
    # Calculate base score from years
    if years_exp < 1:
        base_score = 0.3
    elif years_exp < 3:
        base_score = 0.5
    elif years_exp < 5:
        base_score = 0.7
    elif years_exp < 10:
        base_score = 0.85
    else:
        base_score = 1.0
    
    # Adjust based on JD seniority requirement
    if jd_seniority:
        jd_seniority_lower = jd_seniority.lower()
        for level, (min_years, max_years) in seniority_requirements.items():
            if level in jd_seniority_lower:
                if min_years <= years_exp <= max_years:
                    # Perfect match
                    return min(1.0, base_score * 1.2)
                elif years_exp < min_years:
                    # Underqualified
                    return base_score * 0.7
                else:
                    # Overqualified (still good, but slight penalty)
                    return base_score * 0.9
    
    return base_score


def _calculate_recency_score(
    parsed_data: Optional[Dict[str, Any]],
    keyword: str
) -> float:
    """
    Calculate recency score for a keyword.
    Keywords in recent experience get higher weight.
    
    Returns multiplier from 0.8 to 1.2
    """
    if not parsed_data:
        return 1.0
    
    keyword_lower = keyword.lower()
    keyword_tokens = set(_tokenize(keyword, use_cache=False))
    
    current_year = datetime.now().year
    max_recency_bonus = 0.0
    
    for exp in parsed_data.get("experience", []):
        # Check if keyword appears in this experience
        exp_text = " ".join([
            exp.get("title", ""),
            " ".join(exp.get("bullets", []))
        ]).lower()
        
        if keyword_lower in exp_text or any(
            token in _tokenize(exp_text, use_cache=False)
            for token in keyword_tokens
        ):
            # Get year of this experience
            start_date = exp.get("start_date", "")
            start_year = _extract_year_from_date(start_date) if start_date else None
            
            if start_year:
                years_ago = current_year - start_year
                if years_ago <= 1:
                    recency_bonus = 0.2  # Very recent
                elif years_ago <= 3:
                    recency_bonus = 0.1  # Recent
                elif years_ago <= 5:
                    recency_bonus = 0.0  # Neutral
                else:
                    recency_bonus = -0.2  # Old experience
                
                max_recency_bonus = max(max_recency_bonus, recency_bonus)
    
    return 1.0 + max_recency_bonus


def _extract_year_from_date(date_str: str) -> Optional[int]:
    """Extract year from date string."""
    if not date_str:
        return None
    
    # Try to extract 4-digit year
    match = re.search(r'\b(19|20)\d{2}\b', str(date_str))
    if match:
        return int(match.group())
    
    return None


# =========================================================
# Education and Certification Matching
# =========================================================

def _match_education_requirements(
    parsed_data: Optional[Dict[str, Any]],
    jd_keywords: Dict[str, List[str]]
) -> float:
    """
    Match education requirements from JD.
    Returns score from 0.0 to 1.0
    """
    if not parsed_data:
        return 0.5
    
    education_keywords = [
        "bachelor", "master", "phd", "doctorate",
        "bs", "ms", "mba", "ba", "ma",
        "computer science", "engineering", "degree"
    ]
    
    # Check if JD mentions education requirements
    all_jd_text = " ".join([
        " ".join(jd_keywords.get("required_skills", [])),
        " ".join(jd_keywords.get("optional_skills", [])),
    ]).lower()
    
    has_education_requirement = any(
        edu_kw in all_jd_text for edu_kw in education_keywords
    )
    
    if not has_education_requirement:
        return 1.0  # No requirement = full score
    
    # Check if resume has education
    education = parsed_data.get("education", [])
    if not education:
        return 0.3  # Missing education when required
    
    # Check degree level
    highest_degree = None
    for edu in education:
        degree = edu.get("degree", "").lower()
        if "phd" in degree or "doctorate" in degree:
            highest_degree = "phd"
        elif "master" in degree or "mba" in degree or "ms" in degree or "ma" in degree:
            if highest_degree != "phd":
                highest_degree = "master"
        elif "bachelor" in degree or "bs" in degree or "ba" in degree:
            if highest_degree not in ["phd", "master"]:
                highest_degree = "bachelor"
    
    if highest_degree:
        return 1.0  # Has education
    
    return 0.5  # Partial match


def _match_certifications(
    parsed_data: Optional[Dict[str, Any]],
    jd_keywords: Dict[str, List[str]]
) -> float:
    """
    Match certifications mentioned in JD.
    Returns score from 0.0 to 1.0
    """
    if not parsed_data:
        return 0.5
    
    # Extract certification keywords from JD
    cert_keywords = []
    all_jd_text = " ".join([
        " ".join(jd_keywords.get("required_skills", [])),
        " ".join(jd_keywords.get("optional_skills", [])),
    ]).lower()
    
    # Common certification patterns
    cert_patterns = [
        r"(aws|azure|gcp)\s+certified",
        r"certified\s+(\w+)",
        r"(\w+)\s+certification",
    ]
    
    for pattern in cert_patterns:
        matches = re.findall(pattern, all_jd_text)
        cert_keywords.extend(matches)
    
    if not cert_keywords:
        return 1.0  # No certification requirement
    
    # Check resume certifications
    certifications = parsed_data.get("certifications", [])
    if not certifications:
        return 0.5  # Missing certifications
    
    # Check for matches
    resume_certs_text = " ".join([
        cert.get("name", "") for cert in certifications
    ]).lower()
    
    matches = sum(
        1 for cert_kw in cert_keywords
        if cert_kw.lower() in resume_certs_text
    )
    
    if matches > 0:
        return 1.0  # Has matching certifications
    
    return 0.6  # Has certifications but not matching


# =========================================================
# Skill Proficiency Detection
# =========================================================

def _detect_skill_proficiency(
    keyword: str,
    resume_text: str,
    parsed_data: Optional[Dict[str, Any]] = None
) -> str:
    """
    Detect skill proficiency level from context.
    Returns: "expert" | "intermediate" | "beginner" | "unknown"
    """
    keyword_lower = keyword.lower()
    
    # Expert indicators
    expert_indicators = [
        "architected", "designed", "led", "built from scratch",
        "mentored", "trained", "optimized", "scaled",
        "years of experience", "deep expertise"
    ]
    
    # Intermediate indicators
    intermediate_indicators = [
        "developed", "implemented", "worked with", "used",
        "experience with", "familiar with"
    ]
    
    # Check in experience bullets
    if parsed_data:
        for exp in parsed_data.get("experience", []):
            for bullet in exp.get("bullets", []):
                bullet_lower = bullet.lower()
                if keyword_lower in bullet_lower:
                    # Check for proficiency indicators
                    if any(indicator in bullet_lower for indicator in expert_indicators):
                        return "expert"
                    elif any(indicator in bullet_lower for indicator in intermediate_indicators):
                        return "intermediate"
    
    # Check in summary
    if parsed_data:
        summary = parsed_data.get("summary", "").lower()
        if keyword_lower in summary:
            if any(indicator in summary for indicator in expert_indicators):
                return "expert"
    
    # Default based on frequency
    keyword_count = resume_text.lower().count(keyword_lower)
    if keyword_count >= 3:
        return "intermediate"
    elif keyword_count >= 1:
        return "beginner"
    
    return "unknown"


# =========================================================
# Semantic Matching (using LLM embeddings)
# =========================================================

async def _semantic_similarity(
    keyword: str,
    resume_text: str,
    threshold: float = 0.75
) -> Optional[float]:
    """
    Calculate semantic similarity between keyword and resume using embeddings.
    Falls back to fuzzy matching if embeddings unavailable.
    
    Returns similarity score (0.0 to 1.0) or None if no match
    """
    try:
        # Try to use OpenAI embeddings for semantic matching
        from openai import AsyncOpenAI
        from core.settings import OPENAI_API_KEY
        
        if not OPENAI_API_KEY:
            return None
        
        client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        
        # Get embeddings for keyword and resume snippet
        # For efficiency, only check relevant resume sections
        resume_snippet = resume_text[:2000]  # First 2000 chars
        
        response = await client.embeddings.create(
            model="text-embedding-3-small",
            input=[keyword, resume_snippet]
        )
        
        embeddings = [item.embedding for item in response.data]
        keyword_emb = embeddings[0]
        resume_emb = embeddings[1]
        
        # Calculate cosine similarity
        import numpy as np
        similarity = np.dot(keyword_emb, resume_emb) / (
            np.linalg.norm(keyword_emb) * np.linalg.norm(resume_emb)
        )
        
        if similarity >= threshold:
            return float(similarity)
        
        return None
        
    except Exception as e:
        logger.debug(f"Semantic matching failed, using fallback: {e}")
        # Fallback to fuzzy matching
        from agents.ats_scorer import _find_fuzzy_match
        if _find_fuzzy_match(keyword, _tokenize(resume_text), threshold=0.8):
            return 0.8
        return None


# =========================================================
# Advanced ATS Scorer
# =========================================================

def score_detailed_advanced(
    jd_keywords: Dict[str, List[str]],
    resume_text: str,
    jd_data: Optional[Dict[str, Any]] = None,
    inferred_skills: Optional[List[Dict]] = None,
    parsed_resume_data: Optional[Dict[str, Any]] = None,
    enable_semantic: bool = False,  # Disabled by default for performance
) -> dict:
    """
    Advanced ATS scorer with multi-factor analysis.
    
    Features:
    - Keyword placement weighting
    - Experience depth and recency scoring
    - Education and certification matching
    - Skill proficiency detection
    - Semantic matching (optional)
    - Multi-factor composite scoring
    
    Args:
        jd_keywords: JD keywords organized by category
        resume_text: Resume text
        jd_data: Full JD analysis data (optional, for seniority/education matching)
        inferred_skills: Skills inferred from resume (optional)
        parsed_resume_data: Structured resume data (optional)
        enable_semantic: Enable semantic matching using embeddings (default: True)
    
    Returns:
        Enhanced ATS score with detailed breakdown
    """
    from agents.ats_scorer import score_detailed
    
    # Get base score from existing scorer
    base_result = score_detailed(
        jd_keywords,
        resume_text,
        inferred_skills=inferred_skills,
        parsed_resume_data=parsed_resume_data,
    )
    
    base_score = base_result["score"]
    
    # =========================================================
    # 1. Keyword Placement Weighting
    # =========================================================
    placement_scores = {}
    placement_multiplier = 1.0
    
    tokens = _tokenize(resume_text)
    if parsed_resume_data:
        from agents.resume_structured import create_enhanced_resume_text
        enhanced_text = create_enhanced_resume_text(parsed_resume_data, resume_text)
        tokens = _tokenize(enhanced_text)
    
    placement_weights_sum = 0.0
    placement_matches = 0
    
    for category in ["required_skills", "optional_skills", "tools"]:
        for keyword in jd_keywords.get(category, []):
            match_type = _match_keyword(keyword, tokens)
            if match_type:
                placement = _detect_keyword_placement(
                    keyword,
                    resume_text,
                    parsed_resume_data
                )
                weight = PLACEMENT_WEIGHTS.get(placement, 1.0)
                placement_weights_sum += weight
                placement_matches += 1
                placement_scores[keyword] = {
                    "placement": placement,
                    "weight": weight,
                    "match_type": match_type,
                }
    
    if placement_matches > 0:
        avg_placement_weight = placement_weights_sum / placement_matches
        # Normalize: if avg is 1.5, boost score by 15%
        placement_multiplier = 1.0 + ((avg_placement_weight - 1.0) * 0.3)
    
    # =========================================================
    # 2. Experience Depth Scoring
    # =========================================================
    jd_seniority = jd_data.get("seniority") if jd_data else None
    experience_score = _calculate_experience_score(parsed_resume_data, jd_seniority)
    experience_multiplier = 0.7 + (experience_score * 0.3)  # 0.7 to 1.0 range
    
    # =========================================================
    # 3. Recency Scoring
    # =========================================================
    recency_scores = {}
    avg_recency = 1.0
    
    for category in ["required_skills", "optional_skills", "tools"]:
        for keyword in jd_keywords.get(category, []):
            match_type = _match_keyword(keyword, tokens)
            if match_type:
                recency = _calculate_recency_score(parsed_resume_data, keyword)
                recency_scores[keyword] = recency
    
    if recency_scores:
        avg_recency = sum(recency_scores.values()) / len(recency_scores)
    
    # =========================================================
    # 4. Education and Certification Matching
    # =========================================================
    education_score = _match_education_requirements(parsed_resume_data, jd_keywords)
    certification_score = _match_certifications(parsed_resume_data, jd_keywords)
    
    education_multiplier = 0.8 + (education_score * 0.2)  # 0.8 to 1.0
    certification_multiplier = 0.9 + (certification_score * 0.1)  # 0.9 to 1.0
    
    # =========================================================
    # 5. Skill Proficiency Scoring
    # =========================================================
    proficiency_scores = {}
    
    for category in ["required_skills", "optional_skills", "tools"]:
        for keyword in jd_keywords.get(category, []):
            match_type = _match_keyword(keyword, tokens)
            if match_type:
                proficiency = _detect_skill_proficiency(
                    keyword,
                    resume_text,
                    parsed_resume_data
                )
                proficiency_multiplier = {
                    "expert": 1.2,
                    "intermediate": 1.0,
                    "beginner": 0.85,
                    "unknown": 0.9,
                }.get(proficiency, 1.0)
                proficiency_scores[keyword] = {
                    "level": proficiency,
                    "multiplier": proficiency_multiplier,
                }
    
    avg_proficiency = 1.0
    if proficiency_scores:
        avg_proficiency = sum(
            p["multiplier"] for p in proficiency_scores.values()
        ) / len(proficiency_scores)
    
    # =========================================================
    # 6. Semantic Matching Enhancement (Optional, Async)
    # =========================================================
    semantic_boost = 0.0
    if enable_semantic:
        # Semantic matching requires async - skip for sync version
        # Can be enabled via async wrapper if needed
        logger.debug("Semantic matching requested but disabled in sync version")
        # Fallback: use enhanced fuzzy matching
        from agents.ats_scorer import _find_fuzzy_match
        semantic_matches = 0
        semantic_total = 0
        
        for category in ["required_skills", "optional_skills", "tools"]:
            for keyword in jd_keywords.get(category, []):
                match_type = _match_keyword(keyword, tokens)
                if not match_type:  # Only check unmatched keywords
                    semantic_total += 1
                    # Use enhanced fuzzy matching as fallback
                    fuzzy_match = _find_fuzzy_match(keyword, tokens, threshold=0.80)
                    if fuzzy_match:
                        semantic_matches += 1
                        semantic_boost += 0.5
        
        if semantic_total > 0:
            semantic_boost = (semantic_boost / semantic_total) * 1.5  # Scale to 0-1.5 points
    
    # =========================================================
    # 7. Composite Score Calculation
    # =========================================================
    
    # Apply multipliers to base score
    enhanced_score = base_score
    
    # Apply placement weighting (max +15% boost)
    enhanced_score *= min(placement_multiplier, 1.15)
    
    # Apply experience weighting (max +10% boost)
    enhanced_score *= min(experience_multiplier, 1.10)
    
    # Apply recency weighting (max +10% boost)
    enhanced_score *= min(avg_recency, 1.10)
    
    # Apply education weighting (max +5% boost)
    enhanced_score *= min(education_multiplier, 1.05)
    
    # Apply certification weighting (max +3% boost)
    enhanced_score *= min(certification_multiplier, 1.03)
    
    # Apply proficiency weighting (max +10% boost)
    enhanced_score *= min(avg_proficiency, 1.10)
    
    # Add semantic boost (0-2 points)
    enhanced_score += semantic_boost
    
    # Cap at 100
    enhanced_score = min(100, int(enhanced_score))
    
    # Ensure minimum score if base was good
    if base_score >= 70 and enhanced_score < base_score:
        enhanced_score = max(enhanced_score, base_score - 5)  # Don't penalize too much
    
    # =========================================================
    # 8. Build Enhanced Result
    # =========================================================
    
    result = {
        **base_result,
        "score": enhanced_score,
        "base_score": base_score,
        "score_breakdown": {
            "base_keyword_matching": base_score,
            "placement_boost": round((placement_multiplier - 1.0) * 100, 1),
            "experience_boost": round((experience_multiplier - 1.0) * 100, 1),
            "recency_boost": round((avg_recency - 1.0) * 100, 1),
            "education_boost": round((education_multiplier - 1.0) * 100, 1),
            "certification_boost": round((certification_multiplier - 1.0) * 100, 1),
            "proficiency_boost": round((avg_proficiency - 1.0) * 100, 1),
            "semantic_boost": round(semantic_boost, 1),
        },
        "placement_analysis": placement_scores,
        "proficiency_analysis": proficiency_scores,
        "recency_analysis": recency_scores,
        "experience_score": round(experience_score * 100, 1),
        "education_match": round(education_score * 100, 1),
        "certification_match": round(certification_score * 100, 1),
    }
    
    return result


# Alias for backward compatibility
score_detailed_advanced_sync = score_detailed_advanced

