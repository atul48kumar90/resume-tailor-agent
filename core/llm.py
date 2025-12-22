# core/llm.py
import os
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential

load_dotenv()

_fast_llm = None
_smart_llm = None


def _create_llm(model_name: str):
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=model_name,
        temperature=0.0,
        timeout=30,
        max_retries=0,
        api_key=os.getenv("OPENAI_API_KEY"),
    )


class LLMClient:
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


def fast_llm_call(prompt: str) -> str:
    global _fast_llm
    if _fast_llm is None:
        _fast_llm = LLMClient("gpt-4o-mini")
    return _fast_llm.invoke(prompt)


def smart_llm_call(prompt: str) -> str:
    global _smart_llm
    if _smart_llm is None:
        _smart_llm = LLMClient("gpt-4o")  # Fixed: Changed from "gpt-5.2" to "gpt-4o"
    return _smart_llm.invoke(prompt)
