from agents.jd_analyzer import analyze_jd

def test_jd_analyzer_happy_path(mocker, mock_jd_llm_output):
    spy = mocker.patch(
        "agents.jd_analyzer._llm_call",
        return_value=mock_jd_llm_output,
    )

    jd = "Senior backend engineer with Java and Kubernetes"
    result = analyze_jd(jd)

    assert spy.called
    assert result["role"] == "Backend Engineer"
    assert "Java" in result["required_skills"]



def test_jd_analyzer_handles_invalid_json(mocker):
    mocker.patch(
        "agents.jd_analyzer._llm_call",
        return_value="NOT JSON",
    )

    result = analyze_jd("bad jd")

    assert result["role"] == ""
    assert "error" in result

