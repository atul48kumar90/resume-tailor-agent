# core/llm_async.py
"""
Async LLM client using AsyncOpenAI for better concurrency.

Supports both dependency injection (recommended) and global state (for backward compatibility).
"""
import os
from dotenv import load_dotenv
from tenacity import AsyncRetrying, stop_after_attempt, wait_exponential
from typing import Optional

load_dotenv()

# Global state (for backward compatibility - deprecated, use dependency injection)
_fast_llm: Optional['AsyncLLMClient'] = None
_smart_llm: Optional['AsyncLLMClient'] = None


def _create_async_llm(model_name: str):
    """Create async LLM client using OpenAI's async client."""
    from openai import AsyncOpenAI
    
    return AsyncOpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        timeout=30.0,
        max_retries=0,  # We handle retries with tenacity
    )


class AsyncLLMClient:
    """
    Async LLM client wrapper.
    
    Use this class directly with dependency injection, or use the global functions
    for backward compatibility.
    """
    
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.client: Optional[object] = None
    
    def _get_client(self):
        if self.client is None:
            self.client = _create_async_llm(self.model_name)
        return self.client
    
    async def invoke(self, prompt: str) -> str:
        """Invoke LLM asynchronously with retry logic."""
        client = self._get_client()
        
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=2, max=8),
            reraise=True,
        ):
            with attempt:
                # Use JSON mode for structured outputs (if model supports it)
                # gpt-4o and gpt-4o-mini support response_format
                # Only enable JSON mode if prompt explicitly mentions JSON (OpenAI requirement)
                model_supports_json = self.model_name in ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"]
                prompt_mentions_json = "json" in prompt.lower() or "JSON" in prompt
                use_json_mode = model_supports_json and prompt_mentions_json
                
                if use_json_mode:
                    response = await client.chat.completions.create(
                        model=self.model_name,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.0,
                        response_format={"type": "json_object"},
                    )
                else:
                    response = await client.chat.completions.create(
                        model=self.model_name,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.0,
                    )
                return response.choices[0].message.content


# Global functions (for backward compatibility - prefer dependency injection)
async def fast_llm_call_async(prompt: str, client: Optional[AsyncLLMClient] = None) -> str:
    """
    Fast async LLM call using gpt-4o-mini.
    
    Args:
        prompt: The prompt to send to the LLM
        client: Optional AsyncLLMClient instance (for dependency injection)
    
    Returns:
        LLM response string
    
    Note: Prefer using dependency injection via api.dependencies.get_fast_llm_client_async()
    """
    if client:
        return await client.invoke(prompt)
    
    # Fallback to global state (backward compatibility)
    global _fast_llm
    if _fast_llm is None:
        _fast_llm = AsyncLLMClient("gpt-4o-mini")
    return await _fast_llm.invoke(prompt)


async def smart_llm_call_async(prompt: str, client: Optional[AsyncLLMClient] = None) -> str:
    """
    Smart async LLM call using gpt-4o.
    
    Args:
        prompt: The prompt to send to the LLM
        client: Optional AsyncLLMClient instance (for dependency injection)
    
    Returns:
        LLM response string
    
    Note: Prefer using dependency injection via api.dependencies.get_smart_llm_client_async()
    """
    if client:
        return await client.invoke(prompt)
    
    # Fallback to global state (backward compatibility)
    global _smart_llm
    if _smart_llm is None:
        _smart_llm = AsyncLLMClient("gpt-4o")
    return await _smart_llm.invoke(prompt)

