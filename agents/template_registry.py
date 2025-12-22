TEMPLATES = {
    "classic": {
        "tone": "formal",
        "bullet_style": "full sentences",
    },
    "modern": {
        "tone": "concise",
        "bullet_style": "impact-driven",
    },
    "executive": {
        "tone": "leadership-focused",
        "bullet_style": "results-first",
    },
}


def get_template(template_id: str) -> dict:
    return TEMPLATES.get(template_id, TEMPLATES["classic"])


def rewrite_with_template(text: str, template: dict) -> str:
    prompt = f"""
Rewrite this resume text using:
Tone: {template['tone']}
Bullet style: {template['bullet_style']}

DO NOT add new skills or claims.

{text}
"""
    return core.llm.smart_llm_call(prompt)
