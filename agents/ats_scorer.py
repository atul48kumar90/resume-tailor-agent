import re
from typing import List, Dict, Optional


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
    "spring boot": ["spring", "springboot"],
    "microservices": ["micro-services", "micro services"],
    "postgresql": ["postgres"],
    "javascript": ["js"],
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

def _normalize(text: str) -> str:
    text = re.sub(r"[^a-z0-9+.#]", " ", text.lower())
    return re.sub(r"\s+", " ", text).strip()


def _tokenize(text: str) -> set[str]:
    return set(_normalize(text).split())


# ---------------------------------------------------------
# SAFE composite matcher (FINAL)
# ---------------------------------------------------------

def _match_composite(keyword: str, tokens: set[str]) -> bool:
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

def _match_keyword(keyword: str, tokens: set[str]) -> Optional[str]:
    """
    Returns:
      exact | alias | context | composite | None
    """
    kw = keyword.lower()
    kw_tokens = _tokenize(kw)

    # 1️⃣ Exact
    if kw_tokens and kw_tokens.issubset(tokens):
        return "exact"

    # 2️⃣ Alias
    for alias in KEYWORD_ALIASES.get(kw, []):
        if _tokenize(alias).issubset(tokens):
            return "alias"

    # 3️⃣ Context
    for phrase in KEYWORD_CONTEXT_SIGNALS.get(kw, []):
        if _tokenize(phrase).issubset(tokens):
            return "context"

    # 4️⃣ Composite (SAFE)
    if _match_composite(kw, tokens):
        return "composite"

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
) -> dict:
    tokens = _tokenize(resume_text)

    # 🔥 Evidence-gated inference (NO JD mutation)
    if inferred_skills:
        for s in inferred_skills:
            if s.get("confidence", 0) >= 0.8:
                tokens.update(_tokenize(s["skill"]))

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

    for category, weight in weights.items():
        for kw in jd_keywords.get(category, []):
            match_type = _match_keyword(kw, tokens)

            if match_type:
                matched[category].append(kw)
                score += weight

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

    return {
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
