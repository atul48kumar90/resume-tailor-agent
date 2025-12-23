from agents.role_detector import detect_role


def test_backend_role():
    jd = "Java Spring Boot backend developer"
    resume = "Developed REST APIs using Spring Boot"
    result = detect_role(jd, resume)

    assert result["role"] == "backend"
    assert result["confidence"] > 0.5


def test_infra_role():
    jd = "DevOps engineer Kubernetes AWS"
    resume = "Managed EKS clusters and CI/CD pipelines"
    result = detect_role(jd, resume)

    assert result["role"] == "infra"


def test_fullstack_role():
    jd = "Platform engineer"
    resume = "Built APIs in Java and deployed on Kubernetes"
    result = detect_role(jd, resume)

    assert result["role"] == "fullstack"
