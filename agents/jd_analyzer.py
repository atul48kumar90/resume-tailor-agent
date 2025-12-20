import json
from core.llm import get_llm
from core.prompts import JD_ANALYZER

llm = get_llm()

def analyze_jd(jd: str) -> dict:
    """
    Analyze job description and extract structured requirements
    """
    response = llm.predict(
        JD_ANALYZER.format(jd=jd)
    )
    return json.loads(response)
