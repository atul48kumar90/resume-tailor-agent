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


def rewrite_with_template(text: str, template: dict, original_resume: str = None) -> str:
    """
    Safely rewrite text with template styling, with anti-hallucination guardrails.
    
    Args:
        text: Text to rewrite
        template: Template configuration (tone, bullet_style)
        original_resume: Original resume text for validation (optional but recommended)
    """
    from core.llm_safe import (
        safe_llm_call,
        validate_grounded_in_source,
        create_anti_hallucination_prompt,
    )
    
    # Use original resume for validation if provided, otherwise use text itself
    source_material = original_resume if original_resume else text
    
    # Create prompt with anti-hallucination constraints
    prompt = create_anti_hallucination_prompt(
        base_prompt=f"""Rewrite this resume text using:
Tone: {template['tone']}
Bullet style: {template['bullet_style']}

Only change the style and tone, keep all factual content identical.""",
        source_material=source_material,
        constraints=[
            "DO NOT add new skills or claims",
            "DO NOT invent experience, companies, or metrics",
            "DO NOT change factual content",
            "Only modify tone and style, not facts",
        ],
        output_format="Return only the rewritten text, no JSON or formatting.",
    )
    
    # Validate that rewritten text is grounded in original
    def validate_response(response: str) -> bool:
        if not response or len(response.strip()) < 10:
            return False
        
        # Check if response is grounded in source
        return validate_grounded_in_source(
            response,
            source_material,
            min_similarity=0.4,  # At least 40% word overlap for style changes
        )
    
    # Call LLM with validation
    rewritten = safe_llm_call(
        prompt=prompt,
        validation_fn=validate_response,
        fallback_value=text,  # Return original if validation fails
        max_retries=2,
    )
    
    return rewritten.strip() if rewritten else text.strip()
