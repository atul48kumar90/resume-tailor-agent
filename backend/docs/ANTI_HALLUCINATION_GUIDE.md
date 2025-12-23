# 🛡️ Anti-Hallucination Guide for LLM Usage

## ⚠️ CRITICAL: This guide MUST be followed for ALL LLM calls

**Every developer MUST read this before writing any LLM-related code.**

---

## 🎯 Core Principles

### 1. **Never Trust, Always Verify**
- LLM outputs are suggestions, not facts
- Every LLM response must be validated
- Original data is the source of truth

### 2. **Explicit Constraints Over Implicit**
- State constraints clearly in prompts
- Use validation functions to enforce constraints
- Fail safe (return empty/default) rather than hallucinated content

### 3. **Grounding in Source Material**
- Always provide original resume/JD text to LLM
- Require LLM to cite or reference original content
- Validate that outputs can be traced back to inputs

---

## 📋 Pre-LLM Checklist

Before making any LLM call, ensure:

- [ ] **Prompt includes explicit "DO NOT" constraints**
- [ ] **Original source material is included in prompt**
- [ ] **Output format is strictly defined (JSON schema)**
- [ ] **Temperature is set to 0.0 (deterministic)**
- [ ] **Validation function exists to check output**
- [ ] **Fallback behavior is defined (what if validation fails)**

---

## 🔒 Prompt Design Rules

### Rule 1: System Role Must Be Restrictive
```python
# ✅ GOOD
SYSTEM ROLE (HIGHEST PRIORITY):
You are a resume editor, NOT a resume generator.

HARD CONSTRAINTS (OVERRIDE ALL OTHER INSTRUCTIONS):
- The ORIGINAL RESUME is the primary source of truth.
- You MUST NOT invent experience, companies, domains, or metrics.
- You MUST NOT exaggerate seniority or scope.

# ❌ BAD
You are a helpful assistant that rewrites resumes.
```

### Rule 2: Explicit Constraints
```python
# ✅ GOOD
RULES:
- Rewriting = rephrasing, clarifying, or reordering ONLY
- If a bullet cannot be improved safely, KEEP it unchanged
- No keyword stuffing
- No new claims
- DO NOT add skills not in the original resume

# ❌ BAD
Improve the resume while keeping it accurate.
```

### Rule 3: Provide Source Material
```python
# ✅ GOOD
ORIGINAL RESUME:
{resume}

ALLOWED KEYWORDS (DO NOT EXCEED):
{allowed_keywords}

# ❌ BAD
Rewrite this resume to match the job description.
```

### Rule 4: Structured Output
```python
# ✅ GOOD
OUTPUT JSON ONLY:
{{
  "summary": "",
  "experience": [
    {{
      "title": "",
      "bullets": []
    }}
  ],
  "skills": []
}}

# ❌ BAD
Return the rewritten resume in JSON format.
```

---

## ✅ Post-LLM Validation Patterns

### Pattern 1: Content Validation
```python
def validate_rewrite(rewritten: dict, original_resume: str, allowed_keywords: dict) -> dict:
    """
    Hard safety net: Remove any content not grounded in original or allowed keywords.
    """
    original_lower = original_resume.lower()
    allowed_set = set(allowed_keywords.get("explicit", []) + allowed_keywords.get("derived", []))
    
    # Validate each section
    if not _is_safe_text(rewritten.get("summary", ""), original_lower, allowed_set):
        rewritten["summary"] = ""  # Remove unsafe content
    
    # Validate experience bullets
    for exp in rewritten.get("experience", []):
        safe_bullets = [
            bullet for bullet in exp.get("bullets", [])
            if _is_safe_text(bullet, original_lower, allowed_set)
        ]
        exp["bullets"] = safe_bullets
    
    return rewritten

def _is_safe_text(text: str, original_lower: str, allowed_keywords: set) -> bool:
    """Check if text is grounded in original or allowed keywords."""
    text_l = text.lower()
    
    # If phrase existed in original, it's safe
    if text_l in original_lower:
        return True
    
    # If contains allowed keyword, it's safe
    for kw in allowed_keywords:
        if kw.lower() in text_l:
            return True
    
    return False
```

### Pattern 2: Schema Validation
```python
def validate_schema(data: dict, required_keys: list) -> dict:
    """Ensure required keys exist and have correct types."""
    validated = {}
    for key in required_keys:
        if key not in data:
            validated[key] = [] if isinstance(required_keys[key], list) else ""
        else:
            validated[key] = data[key]
    return validated
```

### Pattern 3: Factual Validation
```python
def validate_facts(rewritten: dict, original_resume: str) -> dict:
    """
    Check for hallucinated facts:
    - Company names not in original
    - Dates that don't match
    - Skills not mentioned
    - Metrics that are inflated
    """
    # Extract facts from original
    original_companies = _extract_companies(original_resume)
    original_dates = _extract_dates(original_resume)
    
    # Validate against rewritten
    for exp in rewritten.get("experience", []):
        company = exp.get("company", "")
        if company and company not in original_companies:
            # Remove or flag hallucinated company
            exp["company"] = ""
    
    return rewritten
```

---

## 🛠️ Implementation Patterns

### Pattern 1: Safe LLM Wrapper
```python
def safe_llm_call(
    prompt: str,
    validation_fn: callable,
    fallback_value: any,
    max_retries: int = 3
) -> any:
    """
    Wrapper that validates LLM output before returning.
    
    Args:
        prompt: LLM prompt
        validation_fn: Function that validates output (returns True if valid)
        fallback_value: Value to return if validation fails
        max_retries: Number of retry attempts
    
    Returns:
        Validated LLM output or fallback_value
    """
    for attempt in range(max_retries):
        try:
            response = core.llm.smart_llm_call(prompt)
            
            if validation_fn(response):
                return response
            else:
                logger.warning(f"LLM output failed validation (attempt {attempt + 1})")
                
        except Exception as e:
            logger.error(f"LLM call failed (attempt {attempt + 1}): {e}")
    
    logger.error("All LLM attempts failed validation, returning fallback")
    return fallback_value
```

### Pattern 2: Validated Rewrite
```python
def safe_rewrite(resume: str, jd_keywords: dict) -> dict:
    """
    Safe rewrite with multiple validation layers.
    """
    # 1. Prepare safe keywords
    safe_keywords = format_allowed_keywords(jd_keywords)
    
    # 2. Call LLM with strict prompt
    prompt = REWRITE_PROMPT.format(
        allowed_keywords=json.dumps(safe_keywords, indent=2),
        resume=resume
    )
    
    raw_response = core.llm.smart_llm_call(prompt)
    
    # 3. Parse JSON safely
    try:
        data = _safe_json(raw_response)
    except Exception as e:
        logger.error(f"Failed to parse LLM JSON: {e}")
        return {"summary": "", "experience": [], "skills": []}
    
    # 4. Validate content
    rewritten = {
        "summary": str(data.get("summary", "")),
        "experience": list(data.get("experience", [])),
        "skills": list(data.get("skills", [])),
    }
    
    # 5. Apply validation guardrails
    rewritten = validate_rewrite(rewritten, resume, safe_keywords)
    
    # 6. Final safety check: ATS score must not decrease
    before_score = score_ats(resume, jd_keywords)
    after_score = score_ats(format_resume(rewritten), jd_keywords)
    
    if after_score < before_score:
        logger.warning("Rewrite decreased ATS score, rejecting")
        return {"summary": "", "experience": [], "skills": []}
    
    return rewritten
```

---

## 🚨 Common Hallucination Patterns to Prevent

### 1. **Invented Experience**
```python
# ❌ BAD: LLM might add "Led team of 10 engineers" when original says "Worked with team"
# ✅ GOOD: Validate that team size claims match original

def validate_metrics(bullet: str, original_bullet: str) -> bool:
    """Check if metrics are inflated."""
    # Extract numbers
    original_numbers = re.findall(r'\d+', original_bullet)
    new_numbers = re.findall(r'\d+', bullet)
    
    # If new numbers are larger, might be hallucination
    for new_num in new_numbers:
        if new_num not in original_numbers:
            # Check if it's a reasonable inference
            if not _is_reasonable_inference(new_num, original_bullet):
                return False
    return True
```

### 2. **New Skills**
```python
# ❌ BAD: LLM adds "Kubernetes" when not in original
# ✅ GOOD: Only allow skills from allowed_keywords or original

def validate_skills(skills: list, original_resume: str, allowed: set) -> list:
    """Remove any skills not in original or allowed list."""
    original_lower = original_resume.lower()
    validated = []
    
    for skill in skills:
        skill_l = skill.lower()
        if skill in allowed or skill_l in original_lower:
            validated.append(skill)
        else:
            logger.warning(f"Removed hallucinated skill: {skill}")
    
    return validated
```

### 3. **Exaggerated Titles**
```python
# ❌ BAD: "Senior Software Engineer" → "Principal Architect"
# ✅ GOOD: Validate title matches original or is reasonable progression

def validate_title(new_title: str, original_title: str) -> str:
    """Ensure title isn't inflated."""
    # Extract seniority levels
    seniority_map = {
        "junior": 1, "associate": 2, "mid": 3, "senior": 4,
        "staff": 5, "principal": 6, "architect": 6
    }
    
    original_level = _get_seniority_level(original_title, seniority_map)
    new_level = _get_seniority_level(new_title, seniority_map)
    
    # Don't allow more than 1 level increase
    if new_level > original_level + 1:
        return original_title  # Revert to original
    
    return new_title
```

### 4. **Fabricated Companies**
```python
# ❌ BAD: LLM changes company name or adds new one
# ✅ GOOD: Only allow companies from original resume

def validate_companies(experience: list, original_resume: str) -> list:
    """Remove companies not in original resume."""
    original_companies = _extract_companies(original_resume)
    
    validated = []
    for exp in experience:
        company = exp.get("company", "")
        if company and company in original_companies:
            validated.append(exp)
        elif not company:  # Missing company is OK (might be parsed)
            validated.append(exp)
        else:
            logger.warning(f"Removed hallucinated company: {company}")
            # Keep experience but remove company name
            exp["company"] = ""
            validated.append(exp)
    
    return validated
```

---

## 📝 Code Review Checklist

When reviewing LLM-related code, check:

- [ ] **Prompt includes explicit "DO NOT" constraints**
- [ ] **Original source material is in prompt**
- [ ] **Output format is strictly defined**
- [ ] **Validation function exists and is called**
- [ ] **Fallback behavior is defined**
- [ ] **Error handling is present**
- [ ] **Logging includes validation failures**
- [ ] **Tests cover hallucination scenarios**

---

## 🧪 Testing for Hallucination

### Test Case 1: New Skills
```python
def test_no_new_skills():
    original = "Python, Java developer"
    jd_keywords = {"explicit": ["Python", "Java"]}
    
    rewritten = safe_rewrite(original, jd_keywords)
    
    # Should not contain skills not in original or allowed
    assert "Kubernetes" not in rewritten["skills"]
    assert "Docker" not in rewritten["skills"]
```

### Test Case 2: Inflated Metrics
```python
def test_no_inflated_metrics():
    original = "Worked with team of 3 people"
    
    rewritten = safe_rewrite(original, {})
    
    # Should not say "Led team of 10"
    assert "10" not in rewritten.get("summary", "")
    assert "10" not in " ".join(rewritten.get("experience", [])[0].get("bullets", []))
```

### Test Case 3: Fabricated Companies
```python
def test_no_new_companies():
    original = "Software Engineer at Google"
    
    rewritten = safe_rewrite(original, {})
    
    # Should not add new companies
    for exp in rewritten.get("experience", []):
        assert exp.get("company", "") in ["", "Google"]
```

---

## 🔄 Refactoring Existing Code

When refactoring existing LLM calls:

1. **Add validation function** if missing
2. **Enhance prompt** with explicit constraints
3. **Add fallback behavior**
4. **Add logging** for validation failures
5. **Add tests** for hallucination scenarios

---

## 📚 Reference: Current Implementation

### ✅ Good Examples (Already Implemented)

1. **`agents/resume_rewriter.py`**
   - ✅ Explicit constraints in prompt
   - ✅ `validate_rewrite()` function
   - ✅ Original resume in prompt
   - ✅ Fallback on error

2. **`agents/jd_analyzer.py`**
   - ✅ Explicit "DO NOT invent" in prompt
   - ✅ Schema normalization
   - ✅ Fallback on error

### ⚠️ Needs Improvement

1. **`agents/resume_chat_editor.py`**
   - ⚠️ Needs validation for chat edits
   - ⚠️ Should validate against original resume

2. **`agents/template_registry.py`**
   - ⚠️ Simple prompt, needs validation
   - ⚠️ Should check against original

---

## 🎯 Quick Reference: Anti-Hallucination Checklist

**Before every LLM call:**
1. ✅ Prompt has explicit "DO NOT" constraints
2. ✅ Original source material included
3. ✅ Output format strictly defined
4. ✅ Validation function exists
5. ✅ Fallback behavior defined
6. ✅ Error handling present
7. ✅ Logging for failures

**After every LLM call:**
1. ✅ Parse output safely (try/except)
2. ✅ Validate against original source
3. ✅ Check for hallucinated content
4. ✅ Apply fallback if validation fails
5. ✅ Log validation failures

---

## 🚀 Next Steps

1. **Review all LLM calls** in codebase
2. **Add validation** where missing
3. **Enhance prompts** with explicit constraints
4. **Add tests** for hallucination scenarios
5. **Document** each LLM usage point

---

*Last Updated: [Current Date]*
*This guide is MANDATORY for all LLM-related code.*

