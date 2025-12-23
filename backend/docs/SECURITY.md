# Security Guide

This document describes the security measures implemented in the Resume Tailor Agent application.

## Input Sanitization

All user inputs are sanitized to prevent various attack vectors:

### 1. XSS (Cross-Site Scripting) Protection

- HTML tags are removed or escaped
- JavaScript event handlers are stripped
- Dangerous HTML elements (`<script>`, `<iframe>`, `<object>`, `<embed>`) are removed

**Usage:**
```python
from core.security import sanitize_text

# Sanitize user input
safe_text = sanitize_text(user_input)
```

### 2. SQL Injection Prevention

- SQLAlchemy uses parameterized queries (primary protection)
- Additional validation layer checks for SQL injection patterns
- Dangerous SQL keywords and patterns are detected and rejected

**Usage:**
```python
from core.security import is_safe_for_sql

if not is_safe_for_sql(user_input):
    raise ValueError("Input contains potentially dangerous SQL patterns")
```

### 3. Command Injection Prevention

- Shell command patterns are detected and rejected
- Special characters that could be used for command injection are sanitized
- Path traversal attempts are blocked

**Usage:**
```python
from core.security import sanitize_filename, validate_file_path

# Sanitize filename
safe_filename = sanitize_filename(user_filename)

# Validate file path
safe_path = validate_file_path(user_path, base_dir="/safe/directory")
```

### 4. File Content Validation

Files are validated beyond just checking extensions:

- **Magic Bytes**: File type is detected by reading file signatures
- **Content Validation**: File content is validated to match expected type
- **Size Limits**: File sizes are strictly enforced
- **Null Byte Detection**: Binary files masquerading as text are detected

**Usage:**
```python
from core.security import validate_file_content

# Validate file before processing
validate_file_content(file_obj, expected_type="pdf", max_size=10*1024*1024)
```

## Input Length Limits

Maximum input lengths are enforced to prevent DoS attacks:

| Input Type | Max Length | Purpose |
|------------|------------|---------|
| User Input | 10,000 chars | General text inputs |
| Job Description | 500,000 chars | JD text (500KB) |
| Resume Text | 1,000,000 chars | Resume text (1MB) |
| Filename | 255 chars | File names |
| User ID | 100 chars | User identifiers |

## File Upload Security

### File Type Validation

1. **Extension Check**: File extension is checked
2. **Magic Bytes**: File signature is verified
3. **Content Validation**: File content is validated to match type
4. **Size Limits**: Maximum file size is enforced (default: 10MB)

### Path Traversal Protection

- Filenames are sanitized to remove path components
- `..`, `/`, `\` are removed from filenames
- File paths are validated to ensure they stay within allowed directories

### Supported File Types

- **PDF**: Validated by `%PDF` header
- **DOCX**: Validated by ZIP signature (`PK\x03\x04`)
- **TXT**: Validated by UTF-8 encoding and absence of null bytes

## Input Validation Functions

### Text Sanitization

```python
from core.security import sanitize_text, sanitize_jd_text, sanitize_resume_text

# General text sanitization
safe_text = sanitize_text(user_input, max_length=10000)

# Job description sanitization
safe_jd = sanitize_jd_text(jd_text)

# Resume text sanitization
safe_resume = sanitize_resume_text(resume_text)
```

### ID Validation

```python
from core.security import validate_user_id, validate_job_id

# Validate user ID (alphanumeric + hyphens/underscores)
user_id = validate_user_id(user_input)

# Validate job ID (UUID format)
job_id = validate_job_id(job_id_string)
```

### Tag Validation

```python
from core.security import validate_tags

# Validate and sanitize comma-separated tags
tag_list = validate_tags("python, fastapi, postgresql")
# Returns: ["python", "fastapi", "postgresql"]
```

### Persona Validation

```python
from core.security import validate_persona

# Validate recruiter persona
persona = validate_persona("technical")  # Must be in allowed list
```

## Security Best Practices

### 1. Always Sanitize User Inputs

```python
# ❌ BAD
@router.post("/example")
def example(user_input: str = Form(...)):
    # Directly using user input
    result = process(user_input)

# ✅ GOOD
@router.post("/example")
def example(user_input: str = Form(...)):
    # Sanitize first
    safe_input = sanitize_text(user_input)
    result = process(safe_input)
```

### 2. Validate File Uploads

```python
# ❌ BAD
@router.post("/upload")
def upload(file: UploadFile = File(...)):
    # No validation
    content = file.read()

# ✅ GOOD
@router.post("/upload")
def upload(file: UploadFile = File(...)):
    # Validate filename
    safe_filename = sanitize_filename(file.filename)
    
    # Validate file content
    validate_file_content(file.file, expected_type="pdf", max_size=10*1024*1024)
    
    content = file.read()
```

### 3. Use Parameterized Queries

SQLAlchemy automatically uses parameterized queries, but always use ORM methods:

```python
# ✅ GOOD - SQLAlchemy handles SQL injection
from db.repositories import get_user_by_id
user = await get_user_by_id(session, user_id)

# ❌ BAD - Never do this
query = f"SELECT * FROM users WHERE id = '{user_id}'"
```

### 4. Validate IDs

```python
# ✅ GOOD
@router.get("/users/{user_id}")
def get_user(user_id: str):
    try:
        user_id = validate_user_id(user_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Use validated ID
    return get_user_data(user_id)
```

## Security Checklist

When adding new endpoints:

- [ ] All text inputs are sanitized
- [ ] File uploads are validated (type, size, content)
- [ ] IDs are validated (format, length)
- [ ] Input lengths are enforced
- [ ] SQL queries use parameterized queries (SQLAlchemy)
- [ ] File paths are validated (no path traversal)
- [ ] Error messages don't leak sensitive information
- [ ] Rate limiting is applied (already done via middleware)

## Common Attack Vectors Prevented

1. **XSS**: HTML/JavaScript in user inputs is removed
2. **SQL Injection**: Parameterized queries + pattern detection
3. **Command Injection**: Shell command patterns are blocked
4. **Path Traversal**: File paths are sanitized
5. **File Upload Attacks**: File content is validated
6. **DoS via Large Inputs**: Input length limits are enforced

## Reporting Security Issues

If you discover a security vulnerability, please:
1. Do not create a public issue
2. Contact the maintainers directly
3. Provide detailed information about the vulnerability
4. Allow time for the issue to be addressed before disclosure

