import pytest


@pytest.fixture
def mock_jd_llm_output():
    return """
    {
      "role": "Backend Engineer",
      "seniority": "Senior",
      "required_skills": ["Java", "Spring Boot", "Kubernetes"],
      "optional_skills": ["Redis"],
      "tools": ["Docker"],
      "responsibilities": ["Build backend services"],
      "ats_keywords": ["Java", "Spring Boot", "Kubernetes", "Redis", "Docker"]
    }
    """


@pytest.fixture
def mock_resume_llm_output():
    return """
    {
      "summary": "Senior backend engineer with strong Java experience.",
      "experience": [
        {
          "title": "Backend Engineer",
          "bullets": [
            "Built scalable Java services using Spring Boot",
            "Deployed applications on Kubernetes"
          ]
        }
      ],
      "skills": ["Java", "Spring Boot", "Kubernetes"]
    }
    """
