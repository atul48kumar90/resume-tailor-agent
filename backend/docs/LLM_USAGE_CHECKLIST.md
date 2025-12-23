# ✅ LLM Usage Checklist

**Use this checklist EVERY TIME you write LLM-related code.**

## Before Writing Code

- [ ] Read `docs/ANTI_HALLUCINATION_GUIDE.md`
- [ ] Understand what hallucination means in this context
- [ ] Know the original source material (resume, JD, etc.)

## Prompt Design

- [ ] Prompt includes explicit "DO NOT" constraints
- [ ] Prompt includes original source material
- [ ] Prompt specifies exact output format (JSON schema)
- [ ] Prompt emphasizes "editor, not generator" role
- [ ] Prompt includes hard constraints section

## Code Implementation

- [ ] Using `core.llm_safe.safe_llm_call()` instead of direct LLM calls
- [ ] Validation function defined and passed to `safe_llm_call()`
- [ ] Fallback value defined (what to return on failure)
- [ ] Original source material passed for validation
- [ ] Error handling with try/except
- [ ] Logging for validation failures

## Validation

- [ ] Content validated against original source
- [ ] Skills validated (no new skills)
- [ ] Facts validated (no invented companies/dates)
- [ ] Metrics validated (no inflated numbers)
- [ ] Schema validated (correct JSON structure)

## Testing

- [ ] Test with hallucination scenarios
- [ ] Test validation function
- [ ] Test fallback behavior
- [ ] Test with edge cases (empty input, malformed JSON)

## Code Review

- [ ] All checklist items completed
- [ ] Code follows patterns in `docs/ANTI_HALLUCINATION_GUIDE.md`
- [ ] Validation is comprehensive
- [ ] Fallback behavior is safe

---

## Quick Reference

### Safe LLM Call Pattern
```python
from core.llm_safe import safe_llm_call, validate_grounded_in_source

def validate_response(response: str) -> bool:
    return validate_grounded_in_source(
        response,
        original_resume,
        allowed_keywords=allowed_set,
        min_similarity=0.3
    )

result = safe_llm_call(
    prompt=enhanced_prompt,
    validation_fn=validate_response,
    fallback_value={"summary": "", "experience": [], "skills": []},
    max_retries=3
)
```

### Prompt Template
```python
from core.llm_safe import create_anti_hallucination_prompt

prompt = create_anti_hallucination_prompt(
    base_prompt="Your task description here",
    source_material=original_resume,
    constraints=[
        "DO NOT invent experience",
        "DO NOT add skills not in original",
        "DO NOT exaggerate metrics",
    ],
    output_format="JSON with keys: summary, experience, skills"
)
```

---

**Remember: When in doubt, be more restrictive. It's better to return less content than hallucinated content.**

