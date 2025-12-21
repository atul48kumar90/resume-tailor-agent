from agents.ats_scorer import score


def test_ats_score_full_match():
    keywords = ["Java", "Spring Boot"]
    resume = "Java developer using Spring Boot"

    result = score(keywords, resume)

    assert result["score"] == 100
    assert result["verdict"] == "Excellent ATS match"


def test_ats_score_partial_match():
    keywords = ["Java", "Kafka"]
    resume = "Java developer"

    result = score(keywords, resume)

    assert result["score"] == 50
    assert result["verdict"] in {"Moderate match", "Weak match"}
