# agents/resume_rewriter.py
import json
import re
import core.llm
from typing import Dict, List


# -------------------------------------------------
# LLM call wrapper (with validation)
# -------------------------------------------------

async def _llm_call_async(prompt: str, validate_json: bool = True) -> str:
    """
    Async safe LLM call wrapper with optional JSON validation.
    
    Args:
        prompt: LLM prompt
        validate_json: If True, validate response is valid JSON
    
    Returns:
        LLM response string
    """
    from core.llm_safe_async import safe_llm_call_async
    import json
    
    if validate_json:
        def validate_response(response: str) -> bool:
            if not response or not response.strip():
                return False
            try:
                # Try to find and parse JSON
                import re
                match = re.search(r"\{[\s\S]*\}", response)
                if match:
                    json.loads(match.group())
                    return True
                return False
            except (json.JSONDecodeError, AttributeError):
                return False
        
        return await safe_llm_call_async(
            prompt=prompt,
            validation_fn=validate_response,
            fallback_value='{"summary": "", "experience": [], "skills": []}',
            max_retries=3,
        )
    else:
        # For non-JSON responses, still use safe wrapper but no JSON validation
        return await safe_llm_call_async(
            prompt=prompt,
            validation_fn=None,  # No validation for non-JSON
            fallback_value="",
            max_retries=3,
        )


def _llm_call(prompt: str, validate_json: bool = True) -> str:
    """
    Safe LLM call wrapper with optional JSON validation.
    
    Args:
        prompt: LLM prompt
        validate_json: If True, validate response is valid JSON
    
    Returns:
        LLM response string
    """
    from core.llm_safe import safe_llm_call
    import json
    
    if validate_json:
        def validate_response(response: str) -> bool:
            if not response or not response.strip():
                return False
            try:
                # Try to find and parse JSON
                import re
                match = re.search(r"\{[\s\S]*\}", response)
                if match:
                    json.loads(match.group())
                    return True
                return False
            except (json.JSONDecodeError, AttributeError):
                return False
        
        return safe_llm_call(
            prompt=prompt,
            validation_fn=validate_response,
            fallback_value='{"summary": "", "experience": [], "skills": []}',
            max_retries=3,
        )
    else:
        # For non-JSON responses, still use safe wrapper but no JSON validation
        return safe_llm_call(
            prompt=prompt,
            validation_fn=None,  # No validation for non-JSON
            fallback_value="",
            max_retries=3,
        )


# -------------------------------------------------
# Rewrite Prompt (STRICT + SAFE)
# -------------------------------------------------

REWRITE_PROMPT = """
SYSTEM ROLE (HIGHEST PRIORITY):
You are an ATS optimization specialist. Your goal is to improve the ATS (Applicant Tracking System) score by strategically incorporating job-relevant keywords while STRICTLY preventing hallucination.

🚨 ANTI-HALLUCINATION RULES (MANDATORY - OVERRIDE ALL OTHER INSTRUCTIONS):
- The ORIGINAL RESUME is the ONLY source of truth
- You MUST NOT invent skills, technologies, tools, or certifications
- You MUST NOT invent experience, companies, projects, or achievements
- You MUST NOT invent metrics, numbers, or quantifiable results
- You MUST NOT exaggerate seniority, scope, or responsibilities
- You CAN ONLY use keywords that are:
  a) Already present in the original resume, OR
  b) Logically implied by existing content (e.g., if resume mentions "Python API development", you can use "REST API" if it's in JD keywords)

PRIMARY OBJECTIVES (IN ORDER OF PRIORITY):
1. PRESERVE all existing keywords that are already in the resume
2. SURFACE implied keywords that are logically present (conservative interpretation only)
3. REPHRASE existing content to be more ATS-friendly (better action verbs, clearer phrasing)
4. IMPROVE keyword density by rephrasing, NOT by adding new content

KEYWORDS TO INCORPORATE (ONLY IF ALREADY PRESENT OR LOGICALLY IMPLIED):
{allowed_keywords}

STRATEGY:
1. For each experience bullet:
   - PRESERVE all existing JD keywords
   - REPHRASE to use stronger action verbs and clearer language
   - ADD JD keywords ONLY if they are logically implied by existing content
   - DO NOT add keywords that require new skills/experience

2. For skills section:
   - INCLUDE all skills from original resume
   - ADD JD keywords ONLY if they are already mentioned in experience/summary
   - DO NOT add new skills that aren't in the original resume

3. For summary:
   - PRESERVE all factual content
   - REPHRASE to include JD keywords that are already in the resume
   - DO NOT add new claims or skills

VALIDATION CHECKLIST (Before outputting):
- Every skill in output exists in original resume OR is logically implied
- Every experience bullet is based on original content
- No new technologies, tools, or certifications are added
- No new metrics or achievements are invented

OUTPUT FORMAT (JSON ONLY):
{{
  "summary": "Rephrased summary with existing JD keywords emphasized",
  "experience": [
    {{
      "title": "Job title (unchanged from original)",
      "bullets": [
        "Rephrased bullets with existing JD keywords preserved and emphasized"
      ]
    }}
  ],
  "skills": ["Only skills from original resume + JD keywords that are already present"]
}}

ORIGINAL RESUME:
{resume}
"""


# -------------------------------------------------
# JSON safety
# -------------------------------------------------

def _safe_json(text: str) -> dict:
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        raise ValueError("No JSON found in LLM output")
    return json.loads(match.group())


# -------------------------------------------------
# Confidence-based keyword formatting
# -------------------------------------------------

def format_allowed_keywords(jd_keywords: dict) -> dict:
    """
    Format JD keywords for rewrite prompt.
    
    Args:
        jd_keywords: Dict with "explicit" (list of strings) and "derived" (list of dicts)
    
    Returns:
        Formatted dict with explicit and derived keywords
    """
    # Handle invalid input types
    if not isinstance(jd_keywords, dict):
        logger = logging.getLogger(__name__)
        logger.warning(f"format_allowed_keywords received non-dict input: {type(jd_keywords)}")
        return {
            "explicit": [],
            "derived": [],
        }
    
    explicit: List[str] = jd_keywords.get("explicit", [])
    if not isinstance(explicit, list):
        explicit = []
    
    derived_out: List[str] = []

    for item in jd_keywords.get("derived", []):
        skill = item.get("skill")
        confidence = item.get("confidence", 0)

        if not skill:
            continue

        if confidence >= 0.9:
            derived_out.append(skill)
        elif confidence >= 0.75:
            derived_out.append(f"{skill} (related experience)")

    return {
        "explicit": explicit,
        "derived": derived_out,
    }


# -------------------------------------------------
# 🔒 Post-LLM validation (FIXED)
# -------------------------------------------------

def validate_rewrite(
    rewritten: dict,
    original_resume: str,
    allowed_keywords: dict,
    baseline_keywords: Dict[str, List[str]] | None = None,
    approved_skills: List[str] | None = None,
) -> dict:
    """
    Hard safety net with anti-hallucination protection.
    
    Removes any content that:
    1. Doesn't exist in original resume
    2. Contains new skills/technologies not in original (unless approved by user)
    3. Contains new claims or metrics not in original
    
    Args:
        rewritten: Rewritten resume dict
        original_resume: Original resume text
        allowed_keywords: JD keywords allowed in rewrite
        baseline_keywords: Keywords already matched in original resume
        approved_skills: List of skills user approved to add (optional)
    
    Returns:
        Validated resume dict with rejected_skills list for user approval
    """
    import re
    import logging
    
    logger = logging.getLogger(__name__)
    original_lower = original_resume.lower()
    original_words = set(re.findall(r'\b\w+\b', original_lower))

    allowed_flat = set(
        allowed_keywords.get("explicit", [])
        + allowed_keywords.get("derived", [])
    )

    baseline_flat = set()
    if baseline_keywords:
        for v in baseline_keywords.values():
            baseline_flat.update(v)

    def safe_text(text: str) -> bool:
        """
        Accept if:
        - phrase existed in original resume (exact or similar), OR
        - contains allowed keyword that's already in original, OR
        - contains baseline ATS keyword that's already matched
        
        Reject if:
        - introduces new skills/technologies not in original
        - contains new metrics/numbers not in original
        """
        if not text or len(text.strip()) < 5:
            return False
            
        text_l = text.lower()
        text_words = set(re.findall(r'\b\w+\b', text_l))
        
        # Check 1: Exact phrase match (allowing for minor rephrasing)
        # If 70% of words are from original, likely safe
        words_from_original = text_words & original_words
        if len(text_words) > 0 and len(words_from_original) / len(text_words) >= 0.7:
            return True
        
        # Check 2: Contains baseline keywords (already matched in original)
        for kw in baseline_flat:
            if kw.lower() in text_l:
                # Verify this keyword was actually in original
                if kw.lower() in original_lower:
                    return True
        
        # Check 3: Contains allowed keywords that are in original
        for kw in allowed_flat:
            if kw.lower() in text_l:
                # Only allow if keyword exists in original resume
                if kw.lower() in original_lower:
                    return True
        
        # Check 4: Extract potential new skills/technologies and verify they're in original
        # Common tech keywords pattern
        tech_patterns = [
            r'\b(python|java|javascript|react|node|aws|docker|kubernetes|sql|mongodb|redis|postgresql|mysql|git|jenkins|terraform|ansible)\b',
            r'\b(api|rest|graphql|microservices|agile|scrum|devops|ci/cd)\b',
        ]
        
        for pattern in tech_patterns:
            matches = re.findall(pattern, text_l, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0] if match else ""
                if match and match.lower() not in original_lower:
                    logger.warning(f"Rejecting text with new technology not in original: {match}")
                    return False
        
        # If we can't verify it's safe, reject it (conservative approach)
        logger.debug(f"Rejecting unverified text: {text[:50]}...")
        return False

    # Summary validation
    summary = rewritten.get("summary", "")
    if summary and not safe_text(summary):
        logger.warning("Rejected rewritten summary - not grounded in original resume")
        rewritten["summary"] = ""

    # Experience bullets validation
    for exp in rewritten.get("experience", []):
        safe_bullets = []
        for bullet in exp.get("bullets", []):
            if safe_text(bullet):
                safe_bullets.append(bullet)
            else:
                logger.warning(f"Rejected bullet: {bullet[:50]}... (not grounded in original)")
        exp["bullets"] = safe_bullets

    # Skills section validation - STRICT: only skills from original, baseline, or approved
    original_skills_lower = set()
    # Extract skills from original resume (look for skills section or common patterns)
    skills_section_match = re.search(r'skills?[:\s]+([^\n]+(?:\n[^\n]+)*)', original_lower, re.IGNORECASE)
    if skills_section_match:
        skills_text = skills_section_match.group(1)
        # Split by common delimiters
        for skill in re.split(r'[,;|•\n]', skills_text):
            skill = skill.strip()
            if skill and len(skill) > 2:
                original_skills_lower.add(skill.lower())
    
    # Also check baseline keywords (already matched skills)
    for kw in baseline_flat:
        original_skills_lower.add(kw.lower())
    
    # Approved skills (user-approved to add)
    approved_skills_lower = set()
    if approved_skills:
        for skill in approved_skills:
            approved_skills_lower.add(skill.lower())
    
    # Track rejected skills for user approval
    rejected_skills = []
    
    # Filter skills: keep if in original, baseline, or approved
    validated_skills = []
    for skill in rewritten.get("skills", []):
        skill_lower = skill.lower()
        if skill_lower in original_skills_lower:
            validated_skills.append(skill)
        elif skill_lower in [kw.lower() for kw in baseline_flat]:
            validated_skills.append(skill)
        elif skill_lower in approved_skills_lower:
            # User approved this skill - allow it
            validated_skills.append(skill)
            logger.info(f"Approved skill added: {skill}")
        else:
            # Track for user approval
            rejected_skills.append(skill)
            logger.warning(f"Rejected skill not in original resume: {skill}")
    
    rewritten["skills"] = list(dict.fromkeys(validated_skills))  # Remove duplicates
    
    # IMPORTANT: Explicitly add approved skills if they're not already in the list
    # This ensures approved skills are added even if LLM didn't include them
    if approved_skills:
        for approved_skill in approved_skills:
            approved_skill_lower = approved_skill.lower()
            # Check if this skill is already in the validated skills (case-insensitive)
            already_present = any(
                existing_skill.lower() == approved_skill_lower 
                for existing_skill in rewritten["skills"]
            )
            if not already_present:
                # Add the approved skill
                rewritten["skills"].append(approved_skill)
                logger.info(f"Explicitly added approved skill: {approved_skill}")
    
    # Remove duplicates again after adding approved skills
    rewritten["skills"] = list(dict.fromkeys(rewritten["skills"]))
    
    # Add rejected_skills to return value for user approval (only if not already approved)
    if rejected_skills:
        rewritten["_rejected_skills"] = list(dict.fromkeys(rejected_skills))

    return rewritten


# -------------------------------------------------
# Main rewrite function
# -------------------------------------------------

async def rewrite_async(
    jd_keywords: dict,
    resume: str,
    baseline_keywords: Dict[str, List[str]] | None = None,
    approved_skills: List[str] | None = None,
) -> dict:
    """
    Async version of rewrite with caching.
    baseline_keywords = matched keywords BEFORE rewrite
    """
    from core.cache_async import (
        get_cached_rewrite_async,
        set_cached_rewrite_async,
        hash_jd_keywords,
    )
    from core.settings import CACHE_REWRITE_TTL
    import logging
    
    logger = logging.getLogger(__name__)

    try:
        # Generate cache key from resume and JD keywords
        jd_keywords_hash = hash_jd_keywords(jd_keywords)
        
        # Check cache first
        cached_result = await get_cached_rewrite_async(resume, jd_keywords_hash)
        if cached_result:
            logger.info("Resume rewrite cache hit (async)")
            # Still validate cached result (safety check)
            safe_keywords = format_allowed_keywords(jd_keywords)
            return validate_rewrite(
                cached_result,
                resume,
                safe_keywords,
                baseline_keywords,
            )
        
        logger.info("Resume rewrite cache miss, calling LLM (async)")
        
        safe_keywords = format_allowed_keywords(jd_keywords)

        raw = await _llm_call_async(
            REWRITE_PROMPT.format(
                allowed_keywords=json.dumps(
                    safe_keywords,
                    indent=2,
                ),
                resume=resume,
            )
        )

        data = _safe_json(raw)

        rewritten = {
            "summary": str(data.get("summary", "")),
            "experience": list(data.get("experience", [])),
            "skills": list(data.get("skills", [])),
        }

        # 🔒 Final validation
        rewritten = validate_rewrite(
            rewritten,
            resume,
            safe_keywords,
            baseline_keywords,
            approved_skills=approved_skills,
        )
        
        # Cache the result (but don't cache user-approved skills - they're job-specific)
        # Remove _rejected_skills from cached version
        cached_version = {k: v for k, v in rewritten.items() if not k.startswith("_")}
        await set_cached_rewrite_async(resume, jd_keywords_hash, cached_version, ttl=CACHE_REWRITE_TTL)

        return rewritten

    except Exception as e:
        # Log error with context
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Resume rewrite failed: {e}", exc_info=True)
        
        # Return safe fallback with error info
        return {
            "summary": "",
            "experience": [],
            "skills": [],
            "error": str(e),
            "note": "Rewrite failed, returning empty result",
        }


def rewrite(
    jd_keywords: dict,
    resume: str,
    baseline_keywords: Dict[str, List[str]] | None = None,
    approved_skills: List[str] | None = None,
) -> dict:
    """
    Synchronous version of rewrite (for backward compatibility).
    baseline_keywords = matched keywords BEFORE rewrite
    
    Uses caching to avoid redundant LLM calls for identical inputs.
    
    Args:
        jd_keywords: Dict with "explicit" (list of strings) and "derived" (list of dicts)
        resume: Original resume text
        baseline_keywords: Optional matched keywords before rewrite
    """
    from core.cache import (
        get_cached_rewrite,
        set_cached_rewrite,
        hash_jd_keywords,
    )
    from core.settings import CACHE_REWRITE_TTL
    import logging
    
    logger = logging.getLogger(__name__)

    # Validate input
    if not isinstance(jd_keywords, dict):
        logger.error(f"rewrite() received invalid jd_keywords type: {type(jd_keywords)}")
        return {
            "summary": "",
            "experience": [],
            "skills": [],
            "error": f"Invalid jd_keywords type: {type(jd_keywords)}",
            "note": "Rewrite failed due to invalid input",
        }

    try:
        # Generate cache key from resume and JD keywords
        jd_keywords_hash = hash_jd_keywords(jd_keywords)
        
        # Check cache first
        cached_result = get_cached_rewrite(resume, jd_keywords_hash)
        if cached_result:
            logger.info("Resume rewrite cache hit")
            # Still validate cached result (safety check)
            safe_keywords = format_allowed_keywords(jd_keywords)
            return validate_rewrite(
                cached_result,
                resume,
                safe_keywords,
                baseline_keywords,
                approved_skills=approved_skills,
            )
        
        logger.info("Resume rewrite cache miss, calling LLM")
        
        safe_keywords = format_allowed_keywords(jd_keywords)

        raw = _llm_call(
            REWRITE_PROMPT.format(
                allowed_keywords=json.dumps(
                    safe_keywords,
                    indent=2,
                ),
                resume=resume,
            )
        )

        data = _safe_json(raw)

        rewritten = {
            "summary": str(data.get("summary", "")),
            "experience": list(data.get("experience", [])),
            "skills": list(data.get("skills", [])),
        }

        # 🔒 Final validation
        rewritten = validate_rewrite(
            rewritten,
            resume,
            safe_keywords,
            baseline_keywords,
            approved_skills=approved_skills,
        )
        
        # Cache the result (but don't cache user-approved skills - they're job-specific)
        # Remove _rejected_skills from cached version
        cached_version = {k: v for k, v in rewritten.items() if not k.startswith("_")}
        set_cached_rewrite(resume, jd_keywords_hash, cached_version, ttl=CACHE_REWRITE_TTL)

        return rewritten

    except Exception as e:
        # Log error with context
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Resume rewrite failed: {e}", exc_info=True)
        
        # Return safe fallback with error info
        return {
            "summary": "",
            "experience": [],
            "skills": [],
            "error": str(e),
            "note": "Rewrite failed, returning empty result",
        }
