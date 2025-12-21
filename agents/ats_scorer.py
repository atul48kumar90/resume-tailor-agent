# agents/ats_scorer.py
import re
from typing import List, Dict


# -----------------------
# Keyword aliases (ATS realism)
# -----------------------

KEYWORD_ALIASES = {
    "kubernetes": ["k8s"],
    "spring boot": ["spring", "springboot"],
    "microservices": ["micro-services", "micro services"],
    "postgresql": ["postgres"],
    "javascript": ["js"],
}

KEYWORD_CONTEXT_SIGNALS = {
    "kubernetes": [
        "container orchestration",
        "eks",
        "gke",
        "aks",
        "helm",
        "containerized workloads",
    ],
    "redis": [
        "cache",
        "caching layer",
        "in-memory store",
    ],
    "microservices": [
        "distributed services",
        "service-oriented",
        "loosely coupled services",
    ],
    "spring boot": [
        "spring",
        "rest api",
        "dependency injection",
    ],
    "docker": [
        "containerized",
        "dockerized",
    ],
}



# -----------------------
# Helpers
# -----------------------

def _normalize(text: str) -> str:
    text = re.sub(r"[^a-z0-9+.#]", " ", text.lower())
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _tokenize(text: str) -> set[str]:
    return set(_normalize(text).split())


def _match_keyword(keyword: str, tokens: set[str]) -> str | None:
    keyword_tokens = _tokenize(keyword)

    # 1️⃣ Exact match
    if keyword_tokens.issubset(tokens):
        return "exact"

    # 2️⃣ Alias match
    for alias in KEYWORD_ALIASES.get(keyword.lower(), []):
        if _tokenize(alias).issubset(tokens):
            return "alias"

    # 3️⃣ Contextual signal match
    for phrase in KEYWORD_CONTEXT_SIGNALS.get(keyword.lower(), []):
        if _tokenize(phrase).issubset(tokens):
            return "context"

    return None


# -----------------------
# Backward-compatible scorer
# -----------------------

def score(keywords: list[str], resume_text: str) -> dict:
    tokens = _tokenize(resume_text)

    matched = [kw for kw in keywords if _match_keyword(kw, tokens)]
    missing = list(set(keywords) - set(matched))

    score_pct = int((len(matched) / max(len(keywords), 1)) * 100)

    return {
        "score": score_pct,
        "matched_keywords": matched,
        "missing_keywords": missing,
        "verdict": (
            "Excellent ATS match"
            if score_pct >= 80
            else "Moderate match"
            if score_pct >= 60
            else "Weak match"
        ),
    }


# -----------------------
# Recruiter-grade ATS scorer
# -----------------------

def score_detailed(
    jd_keywords: Dict[str, List[str]],
    resume_text: str,
) -> dict:
    """
    jd_keywords = {
        "required_skills": [...],
        "optional_skills": [...],
        "tools": [...]
    }
    """
    tokens = _tokenize(resume_text)

    weights = {
        "required_skills": 3.0,
        "tools": 2.0,
        "optional_skills": 1.0,
    }

    total_possible = sum(
        len(jd_keywords.get(k, [])) * w for k, w in weights.items()
    ) or 1.0

    score = 0.0
    matched = {
        "required_skills": [],
        "optional_skills": [],
        "tools": [],
    }
    missing_required = []

    for category, weight in weights.items():
        for kw in jd_keywords.get(category, []):
            if _match_keyword(kw, tokens):
                matched[category].append(kw)
                score += weight
            elif category == "required_skills":
                missing_required.append(kw)

    percentage = int((score / total_possible) * 100)

    # Required-skill floor (real ATS behavior)
    required_total = len(jd_keywords.get("required_skills", []))
    required_coverage = (
        len(matched["required_skills"]) / max(required_total, 1)
    )

    if required_coverage < 0.5:
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


# -----------------------
# Bullet → Keyword Attribution (Improved)
# -----------------------

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
                        "match_type": match_type,  # exact | alias | context
                    })

            bullets.append({
                "text": bullet,
                "matched_keywords": matches,
                "confidence_score": round(
                    sum(
                        1.0 if m["match_type"] == "exact"
                        else 0.7 if m["match_type"] == "alias"
                        else 0.4
                        for m in matches
                    ),
                    2,
                ),
            })

        attributed.append({
            "title": exp.get("title", ""),
            "bullets": bullets,
        })

    return attributed



# -----------------------
# Risk model
# -----------------------

def ats_risk(score: int) -> str:
    if score < 50:
        return "high"
    if score < 70:
        return "medium"
    return "low"
