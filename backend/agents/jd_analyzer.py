# agents/jd_analyzer.py
import json
import re
import core.llm
from typing import Dict, Any


# ------------------------
# LLM wrapper (mockable, with validation)
# ------------------------

def _llm_call(prompt: str) -> str:
    """
    Safe LLM call wrapper with JSON validation for JD analysis.
    (Synchronous version - use _llm_call_async for async)
    
    Args:
        prompt: LLM prompt for JD analysis
    
    Returns:
        LLM response string (should be JSON)
    """
    from core.llm_safe import safe_llm_call
    import json
    import re
    
    def validate_jd_response(response: str) -> bool:
        """
        Validate that response contains valid JSON with expected JD analysis structure.
        """
        if not response or not response.strip():
            return False
        
        try:
            # Try to extract and parse JSON
            match = re.search(r"\{[\s\S]*\}", response)
            if not match:
                return False
            
            data = json.loads(match.group())
            
            # Validate it's an object (not array)
            if not isinstance(data, dict):
                return False
            
            # Should have at least one expected key
            expected_keys = ["role", "seniority", "required_skills", "optional_skills", "tools"]
            if not any(key in data for key in expected_keys):
                return False
            
            return True
            
        except (json.JSONDecodeError, AttributeError, TypeError):
            return False
    
    result = safe_llm_call(
        prompt=prompt,
        validation_fn=validate_jd_response,
        fallback_value='{"role": "", "seniority": "", "required_skills": [], "optional_skills": [], "tools": [], "responsibilities": [], "ats_keywords": {"required_skills": [], "optional_skills": [], "tools": []}}',
        max_retries=3,
    )
    
    # Return as string (safe_llm_call might return dict, so convert)
    if isinstance(result, str):
        return result
    elif isinstance(result, dict):
        return json.dumps(result)
    else:
        return str(result)


async def _llm_call_async(prompt: str) -> str:
    """
    Async safe LLM call wrapper with JSON validation for JD analysis.
    
    Args:
        prompt: LLM prompt for JD analysis
    
    Returns:
        LLM response string (should be JSON)
    """
    from core.llm_safe_async import safe_llm_call_async
    import json
    
    def validate_jd_response(response: str) -> bool:
        """
        Validate that response contains valid JSON with expected JD analysis structure.
        """
        if not response or not response.strip():
            return False
        
        try:
            # Try to extract and parse JSON
            match = re.search(r"\{[\s\S]*\}", response)
            if not match:
                return False
            
            data = json.loads(match.group())
            
            # Validate it's an object (not array)
            if not isinstance(data, dict):
                return False
            
            # Should have at least one expected key
            expected_keys = ["role", "seniority", "required_skills", "optional_skills", "tools"]
            if not any(key in data for key in expected_keys):
                return False
            
            return True
            
        except (json.JSONDecodeError, AttributeError, TypeError):
            return False
    
    return await safe_llm_call_async(
        prompt=prompt,
        validation_fn=validate_jd_response,
        fallback_value='{"role": "", "seniority": "", "required_skills": [], "optional_skills": [], "tools": [], "responsibilities": [], "ats_keywords": {"required_skills": [], "optional_skills": [], "tools": []}}',
        max_retries=3,
    )


# ------------------------
# PROMPT (AS-IS, UNCHANGED)
# ------------------------

JD_PROMPT = """
You are a senior technical recruiter and ATS optimization expert.

TASK:
Analyze the job description and extract structured hiring signals.

STRICT RULES:
- Use ONLY information present or clearly implied in the job description
- Do NOT invent skills, tools, or experience
- Prefer technical, role-specific keywords
- Normalize similar terms (e.g., "Spring" → "Spring Boot")

CLASSIFY SKILLS AS:
- Required skills: explicitly required
- Optional skills: nice-to-have or implied
- Tools: platforms, frameworks, infrastructure
- Responsibilities: concrete job duties

ATS KEYWORDS:
- Include commonly expected keywords for this role
- Only if they are relevant to the JD context

OUTPUT FORMAT:
Return VALID JSON ONLY with the following keys:
role, seniority, required_skills, optional_skills, tools, responsibilities, ats_keywords

JOB DESCRIPTION:
{jd}
"""


# ------------------------
# Ultra-defensive JSON parser
# ------------------------

def _safe_json(text: str) -> Dict[str, Any]:
    if not text or not isinstance(text, str):
        raise ValueError("Empty or invalid LLM response")

    # Extract first JSON object
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        raise ValueError("No JSON object found in LLM output")

    raw = match.group()

    # Fix common LLM formatting errors
    raw = raw.replace("\n", " ")
    raw = re.sub(r",\s*}", "}", raw)
    raw = re.sub(r",\s*]", "]", raw)

    data = json.loads(raw)

    if isinstance(data, list):
        if not data:
            raise ValueError("Empty JSON list returned")
        data = data[0]

    if not isinstance(data, dict):
        raise ValueError("Parsed JSON is not an object")

    return data


# ------------------------
# Schema normalization (CRITICAL FIX)
# ------------------------

def _normalize_schema(data: Dict[str, Any]) -> Dict[str, list]:
    """
    Protects against LLM key drift:
    role vs job_role, required_skills vs requirements, etc.
    """

    key_map = {
        "role": ["role", "job_role", "position"],
        "seniority": ["seniority", "level", "experience_level"],
        "required_skills": ["required_skills", "requirements", "must_have_skills"],
        "optional_skills": ["optional_skills", "nice_to_have", "preferred_skills"],
        "tools": ["tools", "technologies", "platforms"],
        "responsibilities": ["responsibilities", "duties"],
        "ats_keywords": ["ats_keywords", "keywords"],
    }

    normalized = {}
    for target, aliases in key_map.items():
        value = []
        for alias in aliases:
            if alias in data and data[alias]:
                value = data[alias]
                break
        normalized[target] = list(value) if isinstance(value, list) else value

    return normalized


# ------------------------
# Public API
# ------------------------

async def analyze_jd_async(jd: str) -> dict:
    """
    Async version of analyze_jd with caching.
    """
    from core.cache_async import get_cached_jd_async, set_cached_jd_async
    from core.settings import CACHE_JD_TTL
    import logging
    
    logger = logging.getLogger(__name__)
    
    try:
        # Clean JD input
        jd = "\n".join(
            line.strip()
            for line in jd.splitlines()
            if len(line.strip()) > 2
        )

        # Check cache first
        cached_result = await get_cached_jd_async(jd)
        if cached_result:
            logger.info("JD analysis cache hit (async)")
            return cached_result

        logger.info("JD analysis cache miss, calling LLM (async)")
        
        # Call LLM async
        raw = await _llm_call_async(JD_PROMPT.format(jd=jd))
        parsed = _safe_json(raw)
        data = _normalize_schema(parsed)

        # Auto-build ATS keywords if missing
        if not data["ats_keywords"]:
            data["ats_keywords"] = list(
                set(
                    data["required_skills"]
                    + data["optional_skills"]
                    + data["tools"]
                )
            )

        result = {
            "role": str(data["role"]),
            "seniority": str(data["seniority"]),
            "required_skills": data["required_skills"],
            "optional_skills": data["optional_skills"],
            "tools": data["tools"],
            "responsibilities": data["responsibilities"],
            "ats_keywords": data["ats_keywords"],
        }
        
        # Cache the result
        await set_cached_jd_async(jd, result, ttl=CACHE_JD_TTL)
        
        return result

    except Exception as e:
        # Log error with context
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"JD analysis failed: {e}", exc_info=True)
        
        # Hard fail-safe - return empty structure but log the error
        return {
            "role": "",
            "seniority": "",
            "required_skills": [],
            "optional_skills": [],
            "tools": [],
            "responsibilities": [],
            "ats_keywords": {
                "required_skills": [],
                "optional_skills": [],
                "tools": [],
            },
            "error": str(e),
        }


def analyze_jd(jd: str) -> dict:
    """
    Analyze job description with caching.
    
    Returns cached result if available, otherwise analyzes and caches result.
    """
    from core.cache import get_cached_jd, set_cached_jd
    from core.settings import CACHE_JD_TTL
    import logging
    
    logger = logging.getLogger(__name__)
    
    try:
        # Clean JD input
        jd = "\n".join(
            line.strip()
            for line in jd.splitlines()
            if len(line.strip()) > 2
        )

        # Check cache first
        cached_result = get_cached_jd(jd)
        if cached_result:
            logger.info("JD analysis cache hit")
            return cached_result

        logger.info("JD analysis cache miss, calling LLM")
        
        # Call LLM (synchronous for now, can be made async later)
        raw = _llm_call(JD_PROMPT.format(jd=jd))
        parsed = _safe_json(raw)
        data = _normalize_schema(parsed)

        # Ensure ats_keywords is a dict structure (not a list)
        # This is what score_detailed expects
        if not data.get("ats_keywords") or isinstance(data.get("ats_keywords"), list):
            # Convert to dict structure if it's a list or missing
            data["ats_keywords"] = {
                "required_skills": data.get("required_skills", []),
                "optional_skills": data.get("optional_skills", []),
                "tools": data.get("tools", []),
            }
        elif isinstance(data.get("ats_keywords"), dict):
            # Ensure all required keys exist
            if "required_skills" not in data["ats_keywords"]:
                data["ats_keywords"]["required_skills"] = data.get("required_skills", [])
            if "optional_skills" not in data["ats_keywords"]:
                data["ats_keywords"]["optional_skills"] = data.get("optional_skills", [])
            if "tools" not in data["ats_keywords"]:
                data["ats_keywords"]["tools"] = data.get("tools", [])

        result = {
            "role": str(data["role"]),
            "seniority": str(data["seniority"]),
            "required_skills": data["required_skills"],
            "optional_skills": data["optional_skills"],
            "tools": data["tools"],
            "responsibilities": data["responsibilities"],
            "ats_keywords": data["ats_keywords"],
        }
        
        # Cache the result
        set_cached_jd(jd, result, ttl=CACHE_JD_TTL)
        
        return result

    except Exception as e:
        # Log error with context
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"JD analysis failed: {e}", exc_info=True)
        
        # Hard fail-safe - return empty structure but log the error
        return {
            "role": "",
            "seniority": "",
            "required_skills": [],
            "optional_skills": [],
            "tools": [],
            "responsibilities": [],
            "ats_keywords": {
                "required_skills": [],
                "optional_skills": [],
                "tools": [],
            },
            "error": str(e),
        }
