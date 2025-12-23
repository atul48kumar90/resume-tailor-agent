# core/llm_safe.py
"""
Safe LLM wrapper with built-in anti-hallucination guardrails.

⚠️ CRITICAL: All LLM calls should use functions from this module.
See docs/ANTI_HALLUCINATION_GUIDE.md for details.
"""
import logging
from typing import Callable, Any, Optional, Dict
from core.llm import smart_llm_call, fast_llm_call

logger = logging.getLogger(__name__)


def safe_llm_call(
    prompt: str,
    validation_fn: Optional[Callable[[str], bool]] = None,
    fallback_value: Any = None,
    max_retries: int = 3,
    use_fast_model: bool = False,
) -> Any:
    """
    Safe LLM wrapper with validation and fallback.
    
    Args:
        prompt: LLM prompt (should include anti-hallucination constraints)
        validation_fn: Function that validates output (returns True if valid)
        fallback_value: Value to return if validation fails or LLM errors
        max_retries: Number of retry attempts
        use_fast_model: Use fast_llm_call instead of smart_llm_call
    
    Returns:
        Validated LLM output or fallback_value
        
    Example:
        def validate_json(response: str) -> bool:
            try:
                json.loads(response)
                return True
            except:
                return False
        
        result = safe_llm_call(
            prompt="Extract skills as JSON: {resume}",
            validation_fn=validate_json,
            fallback_value={"skills": []}
        )
    """
    llm_call = fast_llm_call if use_fast_model else smart_llm_call
    
    for attempt in range(max_retries):
        try:
            response = llm_call(prompt)
            
            # If no validation function, return response as-is
            if validation_fn is None:
                return response
            
            # Validate response
            if validation_fn(response):
                logger.info(f"LLM call succeeded (attempt {attempt + 1})")
                return response
            else:
                logger.warning(
                    f"LLM output failed validation (attempt {attempt + 1}/{max_retries})"
                )
                
        except Exception as e:
            logger.error(f"LLM call failed (attempt {attempt + 1}/{max_retries}): {e}")
    
    logger.error(
        f"All LLM attempts failed validation or errored, returning fallback value"
    )
    return fallback_value


def validate_grounded_in_source(
    text: str,
    source_text: str,
    allowed_keywords: Optional[set] = None,
    min_similarity: float = 0.3,
) -> bool:
    """
    Validate that text is grounded in source material.
    
    Args:
        text: Text to validate
        source_text: Original source material
        allowed_keywords: Set of allowed keywords (skills, tools, etc.)
        min_similarity: Minimum word overlap ratio (0.0 to 1.0)
    
    Returns:
        True if text is grounded in source, False otherwise
    """
    if not text or not text.strip():
        return True  # Empty text is safe
    
    text_lower = text.lower()
    source_lower = source_text.lower()
    
    # Check if text is substring of source (exact match)
    if text_lower in source_lower:
        return True
    
    # Check word overlap
    text_words = set(text_lower.split())
    source_words = set(source_lower.split())
    
    if text_words:
        overlap = len(text_words & source_words) / len(text_words)
        if overlap >= min_similarity:
            return True
    
    # Check if contains allowed keywords
    if allowed_keywords:
        for keyword in allowed_keywords:
            if keyword.lower() in text_lower:
                return True
    
    return False


def validate_no_new_skills(
    skills: list,
    original_resume: str,
    allowed_skills: Optional[set] = None,
) -> list:
    """
    Remove any skills not in original resume or allowed list.
    
    Args:
        skills: List of skills to validate
        original_resume: Original resume text
        allowed_skills: Set of allowed skills (from JD, etc.)
    
    Returns:
        Filtered list of validated skills
    """
    original_lower = original_resume.lower()
    allowed = allowed_skills or set()
    
    validated = []
    for skill in skills:
        skill_l = skill.lower()
        
        # Allow if in original or in allowed list
        if skill in allowed or skill_l in original_lower:
            validated.append(skill)
        else:
            logger.warning(f"Removed skill not grounded in source: {skill}")
    
    return validated


def validate_no_invented_facts(
    text: str,
    original_resume: str,
    fact_patterns: Optional[Dict[str, Callable]] = None,
) -> bool:
    """
    Validate that text doesn't contain invented facts.
    
    Args:
        text: Text to validate
        original_resume: Original resume text
        fact_patterns: Dict of fact type -> validation function
            Example: {"company": lambda x: x in original_companies}
    
    Returns:
        True if no invented facts detected, False otherwise
    """
    if not fact_patterns:
        return True
    
    for fact_type, validator in fact_patterns.items():
        if not validator(text):
            logger.warning(f"Detected invented {fact_type} in: {text[:100]}")
            return False
    
    return True


def create_anti_hallucination_prompt(
    base_prompt: str,
    source_material: str,
    constraints: Optional[list] = None,
    output_format: Optional[str] = None,
) -> str:
    """
    Create a prompt with anti-hallucination constraints.
    
    Args:
        base_prompt: Base prompt text
        source_material: Original source material (resume, JD, etc.)
        constraints: List of explicit constraints (e.g., ["DO NOT invent skills"])
        output_format: Expected output format (e.g., "JSON with keys: ...")
    
    Returns:
        Enhanced prompt with anti-hallucination guardrails
    """
    constraints = constraints or [
        "DO NOT invent experience, companies, domains, or metrics",
        "DO NOT exaggerate seniority or scope",
        "DO NOT add skills not in the original source material",
    ]
    
    prompt_parts = [
        base_prompt,
        "",
        "HARD CONSTRAINTS (OVERRIDE ALL OTHER INSTRUCTIONS):",
    ]
    
    for constraint in constraints:
        prompt_parts.append(f"- {constraint}")
    
    prompt_parts.append("")
    prompt_parts.append("SOURCE MATERIAL:")
    prompt_parts.append(source_material)
    
    if output_format:
        prompt_parts.append("")
        prompt_parts.append("OUTPUT FORMAT:")
        prompt_parts.append(output_format)
    
    return "\n".join(prompt_parts)


# Export for convenience
__all__ = [
    "safe_llm_call",
    "validate_grounded_in_source",
    "validate_no_new_skills",
    "validate_no_invented_facts",
    "create_anti_hallucination_prompt",
]

