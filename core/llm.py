# core/llm.py
import os
from langchain_openai import ChatOpenAI

def get_llm(temperature: float = 0.0):
    return ChatOpenAI(
        model="gpt-4o-mini",
        temperature=temperature,
        api_key=os.getenv("OPENAI_API_KEY")
    )
