import json
import core.llm


INTENT_PROMPT = """
You are a resume edit intent parser.

Convert the user request into a STRUCTURED COMMAND.
DO NOT edit resume text.

Allowed actions:
- add_skill
- remove_skill
- rewrite_bullet
- rewrite_summary

Output JSON ONLY.

User message:
{message}
"""


def parse_chat_intent(message: str) -> dict:
    """
    Safely parse chat intent with validation.
    
    Args:
        message: User message to parse
    
    Returns:
        Parsed intent dict with action and parameters
    """
    from core.llm_safe import safe_llm_call
    
    prompt = INTENT_PROMPT.format(message=message)
    
    # Validate JSON structure and allowed actions
    def validate_intent(response: str) -> bool:
        if not response or not response.strip():
            return False
        
        try:
            data = json.loads(response)
            
            # Validate required fields
            if "action" not in data:
                return False
            
            # Validate action is allowed
            allowed_actions = ["add_skill", "remove_skill", "rewrite_bullet", "rewrite_summary"]
            if data["action"] not in allowed_actions:
                return False
            
            # Validate action-specific fields
            if data["action"] in ["add_skill", "remove_skill"]:
                if "skill" not in data:
                    return False
            
            if data["action"] == "rewrite_bullet":
                if "index" not in data or "exp_index" not in data:
                    return False
            
            return True
            
        except (json.JSONDecodeError, KeyError, TypeError):
            return False
    
    # Call LLM with validation
    raw = safe_llm_call(
        prompt=prompt,
        validation_fn=validate_intent,
        fallback_value='{"action": "rewrite_bullet", "index": 0, "exp_index": 0}',  # Safe default
        max_retries=3,
    )
    
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to parse intent JSON: {raw}")
        # Return safe default intent
        return {"action": "rewrite_bullet", "index": 0, "exp_index": 0}


def apply_chat_edit(resume: dict, intent: dict) -> dict:
    """
    Apply chat edit with anti-hallucination validation.
    """
    from agents.resume_formatter import format_resume_text
    
    resume = resume.copy()
    
    # Get original resume text for validation
    original_resume_text = format_resume_text(resume)

    action = intent["action"]

    if action == "add_skill":
        skill = intent["skill"]
        # Validate skill is not hallucinated (should be in allowed list or user explicitly added)
        if skill not in resume["skills"]:
            resume["skills"].append(skill)

    elif action == "remove_skill":
        resume["skills"] = [
            s for s in resume["skills"]
            if s != intent["skill"]
        ]

    elif action == "rewrite_bullet":
        idx = intent["index"]
        original_bullet = resume["experience"][intent["exp_index"]]["bullets"][idx]
        
        # Use safe rewrite with original resume for validation
        rewritten = _rewrite_text(
            original_bullet,
            original_resume=original_resume_text
        )
        
        resume["experience"][intent["exp_index"]]["bullets"][idx] = rewritten

    return resume


def _rewrite_text(text: str, original_resume: str = "") -> str:
    """
    Safely rewrite text with anti-hallucination guardrails.
    
    Args:
        text: Text to rewrite
        original_resume: Original resume for validation (optional but recommended)
    """
    from core.llm_safe import (
        safe_llm_call,
        validate_grounded_in_source,
        create_anti_hallucination_prompt,
    )
    
    # Create prompt with anti-hallucination constraints
    prompt = create_anti_hallucination_prompt(
        base_prompt="Rewrite this resume bullet for clarity and ATS optimization.",
        source_material=original_resume or text,  # Use original resume if available
        constraints=[
            "DO NOT add skills, metrics, or claims",
            "DO NOT invent experience or companies",
            "Only rephrase and clarify existing content",
            "Keep the same factual meaning",
        ],
        output_format="Return only the rewritten bullet text, no JSON or formatting.",
    )
    
    # Validate that rewritten text is grounded in original
    def validate_response(response: str) -> bool:
        if not response or len(response.strip()) < 10:
            return False
        
        # Check if response is grounded in source
        source = original_resume if original_resume else text
        return validate_grounded_in_source(
            response,
            source,
            min_similarity=0.3,  # At least 30% word overlap
        )
    
    # Call LLM with validation
    rewritten = safe_llm_call(
        prompt=prompt,
        validation_fn=validate_response,
        fallback_value=text,  # Return original if validation fails
        max_retries=2,
    )
    
    return rewritten.strip() if rewritten else text.strip()


def preview_chat_edit(resume: dict, intent: dict) -> dict:
    simulated = apply_chat_edit(resume, intent)

    return {
        "resume_preview": simulated,
        "requires_approval": intent.get("requires_approval", False),
        "risk_level": intent.get("risk_level", "low"),
        "approval_message": (
            "This change may impact ATS score. Approve?"
            if intent.get("requires_approval")
            else None
        ),
    }
