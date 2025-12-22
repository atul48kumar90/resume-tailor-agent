from agents.ats_scorer import score_detailed


def multi_jd_preview(jds: dict, resume: dict):
    results = {}

    for jd_id, jd_keywords in jds.items():
        results[jd_id] = score_detailed(
            jd_keywords,
            resume_to_text(resume),
        )

    return results
