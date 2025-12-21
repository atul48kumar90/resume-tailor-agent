from agents.skill_inference import derive_safe_skills
from agents.resume_rewriter import rewrite_resume


RESUME = """
Built REST APIs using Spring Boot.
Implemented authentication and authorization.
Deployed services on AWS.
"""


def test_java_is_safely_derived():
    explicit = ["Spring Boot", "REST APIs"]
    derived = derive_safe_skills(explicit, RESUME)

    skills = [d["skill"] for d in derived]
    assert "Java" in skills


def test_graphql_is_not_hallucinated():
    explicit = ["Spring Boot", "REST APIs"]
    derived = derive_safe_skills(explicit, RESUME)

    skills = [d["skill"] for d in derived]
    assert "GraphQL" not in skills


def test_rewrite_does_not_add_unknown_skills():
    allowed = {
        "explicit": ["Spring Boot", "REST APIs"],
        "derived": [{"skill": "Java", "confidence": 0.9}],
    }

    rewritten = rewrite_resume(RESUME, allowed)

    all_text = (
        rewritten["summary"]
        + " ".join(
            bullet
            for exp in rewritten["experience"]
            for bullet in exp.get("bullets", [])
        )
    ).lower()

    assert "graphql" not in all_text
    assert "dynamodb" not in all_text
