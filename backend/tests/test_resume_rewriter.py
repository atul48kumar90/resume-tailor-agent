from agents.resume_rewriter import rewrite


def test_resume_rewriter_success(mocker, mock_resume_llm_output):
    spy = mocker.patch(
        "agents.resume_rewriter._llm_call",
        return_value=mock_resume_llm_output,
    )

    result = rewrite("Java Spring Boot", "Java developer")

    assert spy.called
    assert result["summary"]
    assert len(result["experience"]) == 1



def test_resume_rewriter_failure(mocker):
    mocker.patch(
        "core.llm.smart_llm_call",
        return_value="INVALID",
    )

    result = rewrite("jd", "resume")

    assert result["experience"] == []
    assert "error" in result
