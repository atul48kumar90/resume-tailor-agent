# core/llm.py
"""
Synchronous LLM client module.

Supports both dependency injection (recommended) and global state (for backward compatibility).
"""
import os
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential
from typing import Optional

load_dotenv()

# Global state (for backward compatibility - deprecated, use dependency injection)
_fast_llm: Optional['LLMClient'] = None
_smart_llm: Optional['LLMClient'] = None


def _create_llm(model_name: str):
    """
    Create LLM client with lazy import to avoid fork() issues on macOS.
    
    Langchain imports should happen here (lazy) rather than at module level
    to prevent Objective-C runtime initialization before fork().
    """
    # Lazy import - only import when actually creating LLM client
    # This prevents fork() issues on macOS
    try:
        from langchain_openai import ChatOpenAI
    except ImportError as e:
        raise ImportError(
            f"langchain_openai not installed. Install with: pip install langchain-openai. "
            f"Original error: {e}"
        )

    return ChatOpenAI(
        model=model_name,
        temperature=0.0,
        timeout=30,
        max_retries=0,
        api_key=os.getenv("OPENAI_API_KEY"),
    )


class LLMClient:
    """
    Synchronous LLM client.
    
    Use this class directly with dependency injection, or use the global functions
    for backward compatibility.
    """
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.llm = None

    def _get_llm(self):
        if self.llm is None:
            self.llm = _create_llm(self.model_name)
        return self.llm

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=8),
        reraise=True,
    )
    def invoke(self, prompt: str) -> str:
        return self._get_llm().invoke(prompt).content


# Global functions (for backward compatibility - prefer dependency injection)
def fast_llm_call(prompt: str, client: Optional[LLMClient] = None) -> str:
    """
    Fast LLM call using gpt-4o-mini.
    
    Args:
        prompt: The prompt to send to the LLM
        client: Optional LLMClient instance (for dependency injection)
    
    Returns:
        LLM response string
    
    Note: Prefer using dependency injection via api.dependencies.get_fast_llm_client()
    """
    if client:
        return client.invoke(prompt)
    
    # Fallback to global state (backward compatibility)
    global _fast_llm
    if _fast_llm is None:
        _fast_llm = LLMClient("gpt-4o-mini")
    return _fast_llm.invoke(prompt)


def smart_llm_call(prompt: str, client: Optional[LLMClient] = None) -> str:
    """
    Smart LLM call using gpt-4o.
    
    Args:
        prompt: The prompt to send to the LLM
        client: Optional LLMClient instance (for dependency injection)
    
    Returns:
        LLM response string
    
    Note: Prefer using dependency injection via api.dependencies.get_smart_llm_client()
    """
    if client:
        return client.invoke(prompt)
    
    # Fallback to global state (backward compatibility)
    global _smart_llm
    if _smart_llm is None:
        _smart_llm = LLMClient("gpt-4o")
    return _smart_llm.invoke(prompt)
