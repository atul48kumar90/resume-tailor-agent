# api/chat.py
"""
Chat API for LLM-powered resume editing.
Allows users to chat with LLM to improve resume sections.
"""
from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import logging

from core.llm_safe_async import (
    safe_llm_call_async,
    create_anti_hallucination_prompt_async,
    validate_grounded_in_source_async,
)
from core.security import sanitize_text

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    context: Optional[str] = None  # Resume text or section being edited
    job_id: Optional[str] = None  # Job ID for context
    chat_history: Optional[List[ChatMessage]] = None


class ChatResponse(BaseModel):
    response: str
    suggestions: Optional[List[str]] = None  # Specific suggestions for resume updates


@router.post("/resume-edit", response_model=ChatResponse)
async def chat_resume_edit(request: ChatRequest):
    """
    Chat endpoint for resume editing.
    User can ask LLM to improve, add, or modify resume sections.
    
    Args:
        request: Chat request with message, context (resume text), and history
    
    Returns:
        LLM response with suggestions
    """
    # Sanitize inputs
    user_message = sanitize_text(request.message)
    context = sanitize_text(request.context) if request.context else ""
    
    if not user_message:
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    
    # Build prompt with anti-hallucination constraints
    base_prompt = f"""You are a professional resume editor helping a user improve their resume.

USER REQUEST:
{user_message}

RESUME CONTEXT (the section they're working on):
{context if context else "No specific context provided - user may be asking general questions"}

INSTRUCTIONS:
1. Provide helpful, actionable suggestions for improving the resume
2. If the user asks to add something, suggest how to add it naturally
3. If the user asks to improve something, provide an improved version
4. Keep suggestions grounded in the context provided
5. DO NOT invent experience, companies, or achievements not mentioned
6. DO NOT exaggerate or add false information
7. If asked to add skills, only suggest skills that are reasonable given the context
8. Be concise and professional

OUTPUT FORMAT:
- Provide your response as natural conversation
- If you're suggesting specific text changes, clearly mark them
- If suggesting additions, provide the exact text to add
"""
    
    # Add anti-hallucination constraints
    constraints = [
        "DO NOT invent experience, companies, domains, or metrics",
        "DO NOT exaggerate seniority or scope",
        "DO NOT add skills not reasonably inferable from context",
        "DO NOT create false achievements or certifications",
        "Only suggest improvements based on what's in the context",
    ]
    
    prompt = await create_anti_hallucination_prompt_async(
        base_prompt=base_prompt,
        source_material=context if context else user_message,
        constraints=constraints,
    )
    
    # Validation function: check that response is grounded in context
    async def validate_response(response: str) -> bool:
        """Validate that LLM response is reasonable and not hallucinating."""
        if not response or len(response.strip()) < 10:
            return False
        
        # If context provided, check that response is somewhat related
        if context:
            is_grounded = await validate_grounded_in_source_async(
                text=response,
                source_text=context + " " + user_message,
                min_similarity=0.2,  # Lower threshold for chat (more flexible)
            )
            return is_grounded
        
        # If no context, just check response is not empty
        return len(response.strip()) > 10
    
    # Call LLM with validation
    try:
        response = await safe_llm_call_async(
            prompt=prompt,
            validation_fn=validate_response,
            fallback_value="I apologize, but I'm having trouble processing your request. Could you please rephrase it?",
            max_retries=3,
            use_fast_model=False,  # Use smart model for better quality
        )
        
        # Extract suggestions if response contains actionable items
        suggestions = _extract_suggestions(response)
        
        return ChatResponse(
            response=response,
            suggestions=suggestions if suggestions else None,
        )
        
    except Exception as e:
        logger.error(f"Chat API error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to process chat request. Please try again."
        )


def _extract_suggestions(response: str) -> Optional[List[str]]:
    """
    Extract actionable suggestions from LLM response.
    Looks for patterns like "Add: ..." or "Suggested text: ..."
    """
    suggestions = []
    lines = response.split("\n")
    
    for line in lines:
        line = line.strip()
        # Look for common suggestion patterns
        if line.startswith("Add:") or line.startswith("Suggested:"):
            suggestion = line.split(":", 1)[1].strip() if ":" in line else line
            if suggestion:
                suggestions.append(suggestion)
        elif line.startswith("- ") and len(line) > 10:
            # Bullet point suggestions
            suggestions.append(line[2:].strip())
    
    return suggestions if suggestions else None


@router.post("/apply-suggestion")
async def apply_suggestion(
    job_id: str = Body(...),
    section: str = Body(...),  # "summary", "experience", "skills", etc.
    original_text: str = Body(...),
    suggested_text: str = Body(...),
):
    """
    Apply a suggested change to a resume section.
    Updates the job result with the new text.
    
    Args:
        job_id: Job ID
        section: Resume section to update
        original_text: Original text in that section
        suggested_text: New text to apply
    
    Returns:
        Updated job result
    """
    from api.jobs import get_job, update_job
    from core.security import validate_job_id
    
    # Validate job ID
    try:
        job_id = validate_job_id(job_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Sanitize inputs
    section = sanitize_text(section)
    suggested_text = sanitize_text(suggested_text)
    
    # Get current job result
    job = get_job(job_id)
    if not job or "result" not in job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    result = job["result"]
    resume = result.get("resume", {})
    
    # Update the specified section
    if section == "summary":
        resume["summary"] = suggested_text
    elif section == "skills":
        # Skills is a list, so handle differently
        if isinstance(suggested_text, str):
            # Split by comma if it's a string
            resume["skills"] = [s.strip() for s in suggested_text.split(",") if s.strip()]
        else:
            resume["skills"] = suggested_text
    elif section.startswith("experience."):
        # Format: "experience.0.bullets" or "experience.0.title"
        parts = section.split(".")
        if len(parts) >= 3:
            exp_index = int(parts[1])
            field = parts[2]
            if "experience" in resume and exp_index < len(resume["experience"]):
                if field == "bullets":
                    # Bullets is a list
                    if isinstance(suggested_text, str):
                        resume["experience"][exp_index]["bullets"] = [
                            b.strip() for b in suggested_text.split("\n") if b.strip()
                        ]
                    else:
                        resume["experience"][exp_index]["bullets"] = suggested_text
                else:
                    resume["experience"][exp_index][field] = suggested_text
    else:
        # Generic field update
        resume[section] = suggested_text
    
    # Update job result
    updated_result = {
        **result,
        "resume": resume,
    }
    
    update_job(job_id, updated_result)
    
    return {
        "job_id": job_id,
        "section": section,
        "updated": True,
        "result": updated_result,
    }

