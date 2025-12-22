from agents.ats_scorer import score_detailed


def preview_ats_change(jd_keywords, resume_before, resume_after):
    before = score_detailed(jd_keywords, resume_before)
    after = score_detailed(jd_keywords, resume_after)

    return {
        "before": before["score"],
        "after": after["score"],
        "delta": after["score"] - before["score"],
    }
