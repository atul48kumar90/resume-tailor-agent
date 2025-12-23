import re
from typing import List, Dict, Optional, Set, Any
from difflib import SequenceMatcher


# =========================================================
# SAFE COMPOSITE INFERENCE (ATS-REALISTIC)
# =========================================================
# Composite inference is allowed ONLY when industry truth holds.
# These mappings are conservative and auditable.
COMPOSITE_SKILLS = {
    # Spring Boot cannot exist without Java
    "java": ["spring boot", "spring"],

    # REST APIs almost always exchange JSON
    "json": ["rest api", "rest"],

    # Relational DB inference (generic, safe)
    "relational databases": ["sql", "database", "schema"],

    # Architecture (soft inference)
    "cloud-based architecture design": [
        "distributed",
        "scalable",
        "microservices",
    ],

    "large-scale backend systems": [
        "distributed",
        "scalable",
        "microservices",
    ],

    "documentation best practices": [
        "documentation",
        "design docs",
        "hld",
        "lld",
    ],

    "security best practices": [
        "authentication",
        "authorization",
        "access",
    ],
}


# =========================================================
# Keyword aliases
# =========================================================

KEYWORD_ALIASES = {
    "spring boot": ["spring", "springboot", "springframework"],
    "microservices": ["micro-services", "micro services", "microservice"],
    "postgresql": ["postgres", "postgresql", "pg"],
    "javascript": ["js", "ecmascript"],
    "react": ["reactjs", "react.js"],
    "node.js": ["nodejs", "node", "nodejs"],
    "machine learning": ["ml", "machinelearning"],
    "artificial intelligence": ["ai", "artificialintelligence"],
    "kubernetes": ["k8s", "kube"],
    "amazon web services": ["aws"],
    "microsoft azure": ["azure"],
    "google cloud platform": ["gcp", "google cloud"],
    "application programming interface": ["api", "apis"],
    "representational state transfer": ["rest", "rest api"],
    "graphql": ["graph ql", "gql"],
    "mongodb": ["mongo"],
    "mysql": ["mysql", "my sql"],
    "redis": ["redis cache"],
    "docker": ["docker container", "dockerized"],
}


KEYWORD_CONTEXT_SIGNALS = {
    "docker": ["containerized", "dockerized"],
    "redis": ["cache", "caching", "in-memory"],
    "microservices": ["distributed", "loosely coupled"],
    "spring boot": ["dependency injection", "rest api"],
}


# =========================================================
# Helpers
# =========================================================

# Token cache for performance
_token_cache: Dict[str, Set[str]] = {}

def _normalize(text: str) -> str:
    """
    Normalize text for matching:
    - Convert to lowercase
    - Handle common variations (react.js → reactjs, node.js → nodejs)
    - Remove special chars except alphanumeric, +, #, .
    - Normalize whitespace
    """
    text = text.lower()
    
    # Handle common framework/library variations
    text = re.sub(r"([a-z]+)\.js", r"\1js", text)  # react.js → reactjs
    text = re.sub(r"([a-z]+)\.net", r"\1net", text)  # asp.net → aspnet
    text = re.sub(r"([a-z]+)\.py", r"\1py", text)  # django.py → djangopy (edge case)
    
    # Remove special chars except alphanumeric, +, #, .
    text = re.sub(r"[^a-z0-9+.#]", " ", text)
    
    # Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()
    
    return text


def _tokenize(text: str, use_cache: bool = True) -> Set[str]:
    """
    Tokenize text into a set of tokens.
    Uses both in-memory cache and Redis cache for performance.
    """
    # Check in-memory cache first (fastest)
    if use_cache and text in _token_cache:
        return _token_cache[text]
    
    # Check Redis cache for larger texts
    if use_cache and len(text) > 100:
        from core.cache import get_cached_tokens, set_cached_tokens
        cached_tokens = get_cached_tokens(text)
        if cached_tokens:
            tokens = set(cached_tokens)
            # Also store in memory cache for quick access
            if len(text) < 1000:
                _token_cache[text] = tokens
            return tokens
    
    # Tokenize the text
    normalized = _normalize(text)
    tokens = set(normalized.split())
    
    # Cache the result
    if use_cache:
        # In-memory cache for smaller texts
        if len(text) < 1000:
            _token_cache[text] = tokens
        
        # Redis cache for all texts > 100 chars
        if len(text) > 100:
            from core.cache import set_cached_tokens
            from core.settings import CACHE_NORMALIZED_TTL
            set_cached_tokens(text, list(tokens), ttl=CACHE_NORMALIZED_TTL)
    
    return tokens


def _fuzzy_ratio(str1: str, str2: str) -> float:
    """Calculate similarity ratio between two strings (0.0 to 1.0)."""
    return SequenceMatcher(None, str1.lower(), str2.lower()).ratio()


def _find_fuzzy_match(keyword: str, tokens: Set[str], threshold: float = 0.85) -> Optional[str]:
    """
    Find fuzzy matches for a keyword in tokens.
    
    Args:
        keyword: The keyword to match
        tokens: Set of tokens from resume
        threshold: Minimum similarity ratio (0.0 to 1.0)
    
    Returns:
        Matched token if found, None otherwise
    """
    kw_normalized = _normalize(keyword)
    kw_tokens = kw_normalized.split()
    
    # For multi-word keywords, check if any token matches
    if len(kw_tokens) > 1:
        # Check if all tokens are present (exact match already handled)
        # For fuzzy, check if most tokens match
        matches = sum(1 for kw_t in kw_tokens if any(
            _fuzzy_ratio(kw_t, token) >= threshold for token in tokens
        ))
        if matches >= max(1, len(kw_tokens) * 0.7):  # 70% of tokens match
            return "fuzzy"
    
    # For single-word keywords, check direct fuzzy match
    for token in tokens:
        ratio = _fuzzy_ratio(kw_normalized, token)
        if ratio >= threshold:
            return "fuzzy"
    
    # Also check if keyword is substring or token is substring (for abbreviations)
    kw_normalized_no_space = kw_normalized.replace(" ", "")
    for token in tokens:
        token_no_space = token.replace(" ", "")
        # Check if one contains the other (for abbreviations like ML vs Machine Learning)
        if len(kw_normalized_no_space) >= 3 and len(token_no_space) >= 3:
            if kw_normalized_no_space in token_no_space or token_no_space in kw_normalized_no_space:
                # Verify they're similar enough
                if _fuzzy_ratio(kw_normalized_no_space, token_no_space) >= 0.75:
                    return "fuzzy"
    
    return None


# ---------------------------------------------------------
# SAFE composite matcher (FINAL)
# ---------------------------------------------------------

def _match_composite(keyword: str, tokens: Set[str]) -> bool:
    """
    SAFE composite inference (ATS-realistic)

    Rules:
    - Token overlap (not full subset)
    - Strong-signal shortcut
    - Otherwise ≥50% signal coverage
    """

    parts = COMPOSITE_SKILLS.get(keyword.lower())
    if not parts:
        return False

    hits = 0
    for p in parts:
        p_tokens = set(_tokenize(p))
        if tokens & p_tokens:
            hits += 1

    # Strong-signal shortcut (e.g. Spring → Java)
    if hits >= 1 and len(parts) <= 2:
        return True

    return hits >= max(1, len(parts) // 2)


# ---------------------------------------------------------
# Keyword matcher
# ---------------------------------------------------------

def _match_keyword(keyword: str, tokens: Set[str], enable_fuzzy: bool = True) -> Optional[str]:
    """
    Match keyword against resume tokens using multiple strategies.
    
    Returns:
      exact | alias | context | composite | fuzzy | None
    
    Matching order (most confident first):
    1. Exact match (all tokens present)
    2. Alias match (known aliases)
    3. Context match (contextual signals)
    4. Composite match (inferred from related skills)
    5. Fuzzy match (typos/variations, if enabled)
    """
    kw = keyword.lower()
    kw_tokens = _tokenize(kw, use_cache=False)

    # 1️⃣ Exact (highest confidence)
    if kw_tokens and kw_tokens.issubset(tokens):
        return "exact"

    # 2️⃣ Alias (high confidence)
    for alias in KEYWORD_ALIASES.get(kw, []):
        alias_tokens = _tokenize(alias, use_cache=False)
        if alias_tokens.issubset(tokens):
            return "alias"

    # 3️⃣ Context (medium-high confidence)
    for phrase in KEYWORD_CONTEXT_SIGNALS.get(kw, []):
        phrase_tokens = _tokenize(phrase, use_cache=False)
        if phrase_tokens.issubset(tokens):
            return "context"

    # 4️⃣ Composite (medium confidence, safe inference)
    if _match_composite(kw, tokens):
        return "composite"

    # 5️⃣ Fuzzy (lower confidence, handles typos/variations)
    if enable_fuzzy:
        fuzzy_match = _find_fuzzy_match(keyword, tokens, threshold=0.85)
        if fuzzy_match:
            return "fuzzy"

    return None


# =========================================================
# Simple scorer (debug only)
# =========================================================

def score(keywords: list[str], resume_text: str) -> dict:
    tokens = _tokenize(resume_text)
    matched = [kw for kw in keywords if _match_keyword(kw, tokens)]
    missing = list(set(keywords) - set(matched))

    return {
        "score": int((len(matched) / max(len(keywords), 1)) * 100),
        "matched_keywords": matched,
        "missing_keywords": missing,
    }


# =========================================================
# Recruiter-grade ATS scorer (PRODUCTION)
# =========================================================

def score_detailed(
    jd_keywords: Dict[str, List[str]],
    resume_text: str,
    inferred_skills: Optional[List[Dict]] = None,
    parsed_resume_data: Optional[Dict[str, Any]] = None,
) -> dict:
    """
    Calculate detailed ATS score with caching.
    
    Caches results for identical resume+JD keyword pairs to avoid redundant computation.
    """
    from core.cache import (
        get_cached_ats_score,
        set_cached_ats_score,
        hash_jd_keywords,
    )
    from core.settings import CACHE_ATS_TTL
    import logging
    
    logger = logging.getLogger(__name__)
    
    # Generate cache key (note: inferred_skills not included in cache key for simplicity)
    # If inferred_skills are important, they should be included in the hash
    jd_keywords_hash = hash_jd_keywords(jd_keywords)
    
    # Check cache first (only if no inferred_skills, as they affect the score)
    if not inferred_skills:
        cached_result = get_cached_ats_score(resume_text, jd_keywords_hash)
        if cached_result:
            logger.info("ATS score cache hit")
            return cached_result
    
    logger.info("ATS score cache miss, computing score")
    
    # Enhance resume text with structured data if available
    if parsed_resume_data:
        from agents.resume_structured import create_enhanced_resume_text, extract_skills_from_structured
        enhanced_text = create_enhanced_resume_text(parsed_resume_data, resume_text)
        tokens = _tokenize(enhanced_text)
        # Also add structured skills directly to tokens
        structured_skills = extract_skills_from_structured(parsed_resume_data)
        for skill in structured_skills:
            tokens.update(_tokenize(skill))
    else:
        tokens = _tokenize(resume_text)

    # 🔥 Evidence-gated inference (NO JD mutation)
    if inferred_skills:
        for s in inferred_skills:
            if s.get("confidence", 0) >= 0.8:
                tokens.update(_tokenize(s["skill"]))
    
    # Add structured skills to tokens if available
    if parsed_resume_data:
        from agents.resume_structured import extract_skills_from_structured
        structured_skills = extract_skills_from_structured(parsed_resume_data)
        for skill in structured_skills:
            tokens.update(_tokenize(skill))

    # Normalize jd_keywords - handle both dict and list formats
    if isinstance(jd_keywords, list):
        # If it's a list, convert to dict structure
        logger.warning("jd_keywords is a list, converting to dict structure")
        jd_keywords = {
            "required_skills": jd_keywords,
            "optional_skills": [],
            "tools": [],
        }
    elif not isinstance(jd_keywords, dict):
        # If it's neither dict nor list, create empty structure
        logger.warning(f"jd_keywords is {type(jd_keywords)}, using empty dict")
        jd_keywords = {
            "required_skills": [],
            "optional_skills": [],
            "tools": [],
        }

    weights = {
        "required_skills": 3.0,
        "tools": 2.0,
        "optional_skills": 1.0,
    }

    total_possible = sum(
        len(jd_keywords.get(cat, [])) * w
        for cat, w in weights.items()
    ) or 1.0

    score = 0.0
    matched = {k: [] for k in weights}
    missing_required = []
    
    # Match type weights (fuzzy matches get reduced weight)
    match_weights = {
        "exact": 1.0,
        "alias": 1.0,
        "context": 0.9,
        "composite": 0.85,
        "fuzzy": 0.75,  # Lower confidence for fuzzy matches
    }

    for category, weight in weights.items():
        for kw in jd_keywords.get(category, []):
            match_type = _match_keyword(kw, tokens)

            if match_type:
                matched[category].append(kw)
                # Apply match type weight (fuzzy gets less credit)
                match_weight = match_weights.get(match_type, 1.0)
                score += weight * match_weight

            elif category == "required_skills":
                # 🚫 Do not hard-block composite / architecture skills
                if kw.lower() not in COMPOSITE_SKILLS:
                    missing_required.append(kw)

    percentage = int((score / total_possible) * 100)

    # ATS floor logic (realistic)
    required_total = len(jd_keywords.get("required_skills", []))
    required_coverage = len(matched["required_skills"]) / max(required_total, 1)

    if required_coverage < 0.4:
        percentage = min(percentage, 45)

    result = {
        "score": percentage,
        "risk": ats_risk(percentage),
        "matched_keywords": matched,
        "missing_required": missing_required,
        "coverage": {
            "required": f"{len(matched['required_skills'])}/{required_total}",
            "tools": f"{len(matched['tools'])}/{len(jd_keywords.get('tools', []))}",
            "optional": f"{len(matched['optional_skills'])}/{len(jd_keywords.get('optional_skills', []))}",
        },
        "warnings": (
            ["Missing critical required skills"]
            if missing_required
            else []
        ),
    }
    
    # Cache the result (only if no inferred_skills)
    if not inferred_skills:
        set_cached_ats_score(resume_text, jd_keywords_hash, result, ttl=CACHE_ATS_TTL)
    
    return result


# =========================================================
# Bullet → Keyword attribution
# =========================================================

def attribute_keywords_to_bullets(
    jd_keywords: Dict[str, List[str]],
    experience: list[dict],
) -> list[dict]:
    attributed = []

    all_keywords = (
        jd_keywords.get("required_skills", [])
        + jd_keywords.get("optional_skills", [])
        + jd_keywords.get("tools", [])
    )

    for exp in experience:
        bullets = []

        for bullet in exp.get("bullets", []):
            tokens = _tokenize(bullet)
            matches = []

            for kw in all_keywords:
                match_type = _match_keyword(kw, tokens)
                if match_type:
                    matches.append({
                        "keyword": kw,
                        "match_type": match_type,
                    })

            bullets.append({
                "text": bullet,
                "matched_keywords": matches,
            })

        attributed.append({
            "title": exp.get("title", ""),
            "bullets": bullets,
        })

    return attributed


# =========================================================
# Risk model
# =========================================================

def ats_risk(score: int) -> str:
    if score < 50:
        return "high"
    if score < 70:
        return "medium"
    return "low"
