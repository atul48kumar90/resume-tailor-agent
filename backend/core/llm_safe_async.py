# core/llm_safe_async.py
"""
Async safe LLM wrapper with built-in anti-hallucination guardrails.
"""
import logging
import inspect
from typing import Callable, Any, Optional, Dict, Awaitable, Union
from core.llm_async import smart_llm_call_async, fast_llm_call_async

logger = logging.getLogger(__name__)


async def safe_llm_call_async(
    prompt: str,
    validation_fn: Optional[Union[Callable[[str], bool], Callable[[str], Awaitable[bool]]]] = None,
    fallback_value: Any = None,
    max_retries: int = 3,
    use_fast_model: bool = False,
) -> Any:
    """
    Async safe LLM wrapper with validation and fallback.
    
    Args:
        prompt: LLM prompt (should include anti-hallucination constraints)
        validation_fn: Function that validates output (returns True if valid). Can be sync or async.
        fallback_value: Value to return if validation fails or LLM errors
        max_retries: Number of retry attempts
        use_fast_model: Use fast_llm_call_async instead of smart_llm_call_async
    
    Returns:
        Validated LLM output or fallback_value
    """
    llm_call = fast_llm_call_async if use_fast_model else smart_llm_call_async
    
    for attempt in range(max_retries):
        try:
            response = await llm_call(prompt)
            
            # If no validation function, return response as-is
            if validation_fn is None:
                return response
            
            # Validate response - handle both sync and async validation functions
            if inspect.iscoroutinefunction(validation_fn):
                is_valid = await validation_fn(response)
            else:
                is_valid = validation_fn(response)
            
            if is_valid:
                logger.info(f"Async LLM call succeeded (attempt {attempt + 1})")
                return response
            else:
                # Log response preview for debugging (first 500 chars)
                response_preview = response[:500] if response else "None"
                logger.warning(
                    f"Async LLM output failed validation (attempt {attempt + 1}/{max_retries}). "
                    f"Response preview: {response_preview}..."
                )
                
        except Exception as e:
            logger.error(f"Async LLM call failed (attempt {attempt + 1}/{max_retries}): {e}")
    
    logger.error(
        f"All async LLM attempts failed validation or errored, returning fallback value"
    )
    return fallback_value


async def validate_grounded_in_source_async(
    text: str,
    source_text: str,
    allowed_keywords: Optional[set] = None,
    min_similarity: float = 0.3,
) -> bool:
    """
    Async version of validate_grounded_in_source.
    (Same logic, just async for consistency)
    """
    from core.llm_safe import validate_grounded_in_source
    # This is CPU-bound, but we keep it async for API consistency
    return validate_grounded_in_source(text, source_text, allowed_keywords, min_similarity)


async def create_anti_hallucination_prompt_async(
    base_prompt: str,
    source_material: str,
    constraints: Optional[list] = None,
    output_format: Optional[str] = None,
) -> str:
    """
    Async version of create_anti_hallucination_prompt.
    (Same logic, just async for consistency)
    """
    from core.llm_safe import create_anti_hallucination_prompt
    return create_anti_hallucination_prompt(base_prompt, source_material, constraints, output_format)

