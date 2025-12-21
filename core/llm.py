# core/llm.py
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

load_dotenv()


class LLMClient:
    def __init__(self, model_name: str):
        self.llm = ChatOpenAI(
            model=model_name,
            temperature=0.0,
            timeout=30,
            max_retries=0,
            api_key=os.getenv("OPENAI_API_KEY"),
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=8),
        reraise=True,
    )
    def invoke(self, prompt: str) -> str:
        return self.llm.invoke(prompt).content


_fast_llm = LLMClient("gpt-4o-mini")
_smart_llm = LLMClient("gpt-5.2")


def fast_llm_call(prompt: str) -> str:
    return _fast_llm.invoke(prompt)


def smart_llm_call(prompt: str) -> str:
    return _smart_llm.invoke(prompt)
