from agents.recruiter_persona import tune


def test_persona_fintech():
    resume = {"summary": "Backend engineer"}
    tuned = tune(resume, "fintech")

    assert "persona_emphasis" in tuned
    assert "security" in tuned["persona_emphasis"]


def test_persona_default():
    resume = {}
    tuned = tune(resume, "unknown")

    assert tuned["persona_emphasis"] == []
