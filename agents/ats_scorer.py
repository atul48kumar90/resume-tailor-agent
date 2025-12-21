# agents/ats_scorer.py
def score(keywords, resume_text):
    resume = resume_text.lower()
    matched = [k for k in keywords if k.lower() in resume]
    missing = [k for k in keywords if k.lower() not in resume]

    return {
        "match_percent": int(len(matched) / max(len(keywords), 1) * 100),
        "missing_keywords": missing,
    }
