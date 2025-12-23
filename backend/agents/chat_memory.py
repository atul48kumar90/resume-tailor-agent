from collections import defaultdict

# resume_id -> chat history
_chat_memory = defaultdict(list)

MAX_MESSAGES = 20


def add_chat_message(resume_id: str, role: str, content: str):
    _chat_memory[resume_id].append({
        "role": role,
        "content": content,
    })
    _chat_memory[resume_id] = _chat_memory[resume_id][-MAX_MESSAGES:]


def get_chat_memory(resume_id: str) -> list[dict]:
    return _chat_memory[resume_id]


def clear_chat_memory(resume_id: str):
    _chat_memory[resume_id].clear()
