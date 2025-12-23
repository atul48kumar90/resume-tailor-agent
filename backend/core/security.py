# core/security.py
"""
Input sanitization and security utilities.

Provides functions to sanitize user inputs and prevent:
- XSS (Cross-Site Scripting) attacks
- SQL injection (though SQLAlchemy handles this, we add extra validation)
- Command injection
- Path traversal attacks
- Malicious file content
"""
import re
import html
import logging
from typing import Optional, List
from pathlib import Path
import os

logger = logging.getLogger(__name__)

# Maximum input lengths
MAX_TEXT_LENGTH = 1000000  # 1MB of text
MAX_FILENAME_LENGTH = 255
MAX_USER_INPUT_LENGTH = 10000
MAX_JD_LENGTH = 500000  # 500KB for job descriptions

# Allowed characters for filenames (prevent path traversal)
ALLOWED_FILENAME_CHARS = re.compile(r'^[a-zA-Z0-9._-]+$')

# Dangerous patterns to detect
SQL_INJECTION_PATTERNS = [
    r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE)\b)",
    r"(--|#|/\*|\*/)",
    r"(\b(UNION|OR|AND)\s+\d+\s*=\s*\d+)",
    r"('|(\\')|(;)|(\\;))",
]

XSS_PATTERNS = [
    r"<script[^>]*>.*?</script>",
    r"javascript:",
    r"on\w+\s*=",  # onclick=, onerror=, etc.
    r"<iframe[^>]*>",
    r"<object[^>]*>",
    r"<embed[^>]*>",
]

COMMAND_INJECTION_PATTERNS = [
    # Only match command separators when they appear in suspicious contexts
    r"[;&|]\s*(cat|ls|rm|mv|cp|chmod|chown|sudo|su|wget|curl|python|bash|sh)\s+",
    r"`[^`]*`",  # Backtick command execution (more specific)
    r"\$\{[^}]*\}",  # Variable expansion in suspicious context
    # Match shell command words followed by arguments (not just standalone words)
    r"\b(cat|ls|rm|mv|cp|chmod|chown|sudo|su|wget|curl)\s+[^\s]+",  # Command with argument
]


# ============================================================
# Text Sanitization
# ============================================================

def sanitize_text(text: str, max_length: Optional[int] = None, allow_html: bool = False) -> str:
    """
    Sanitize text input to prevent XSS and other attacks.
    
    Args:
        text: Input text to sanitize
        max_length: Maximum allowed length (default: MAX_USER_INPUT_LENGTH)
        allow_html: If True, escape HTML instead of removing it
    
    Returns:
        Sanitized text
    
    Raises:
        ValueError: If text contains dangerous patterns or exceeds max length
    """
    if not isinstance(text, str):
        raise ValueError("Input must be a string")
    
    max_len = max_length or MAX_USER_INPUT_LENGTH
    
    # Check length
    if len(text) > max_len:
        logger.warning(f"Input text exceeds maximum length: {len(text)} > {max_len}")
        raise ValueError(f"Input text exceeds maximum length of {max_len} characters")
    
    # Remove null bytes
    text = text.replace('\x00', '')
    
    # Check for SQL injection patterns
    for pattern in SQL_INJECTION_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            logger.warning(f"Potential SQL injection detected in input")
            raise ValueError("Input contains potentially dangerous SQL patterns")
    
    # Check for command injection patterns
    for pattern in COMMAND_INJECTION_PATTERNS:
        if re.search(pattern, text):
            logger.warning(f"Potential command injection detected in input")
            raise ValueError("Input contains potentially dangerous command patterns")
    
    # Handle HTML/XSS
    if allow_html:
        # Escape HTML entities
        text = html.escape(text)
    else:
        # Remove XSS patterns
        for pattern in XSS_PATTERNS:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.DOTALL)
    
    # Remove control characters (except newlines and tabs)
    text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\t')
    
    return text.strip()


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent path traversal and other attacks.
    
    Args:
        filename: Original filename
    
    Returns:
        Sanitized filename
    
    Raises:
        ValueError: If filename is invalid or dangerous
    """
    if not filename:
        raise ValueError("Filename cannot be empty")
    
    # Remove path components
    filename = os.path.basename(filename)
    
    # Check length
    if len(filename) > MAX_FILENAME_LENGTH:
        raise ValueError(f"Filename exceeds maximum length of {MAX_FILENAME_LENGTH} characters")
    
    # Check for path traversal attempts
    if '..' in filename or '/' in filename or '\\' in filename:
        logger.warning(f"Path traversal attempt detected: {filename}")
        raise ValueError("Filename contains invalid path components")
    
    # Remove dangerous characters
    filename = re.sub(r'[<>:"|?*\x00-\x1f]', '', filename)
    
    # Ensure it's not empty after sanitization
    if not filename or filename.startswith('.'):
        raise ValueError("Invalid filename after sanitization")
    
    return filename


def sanitize_jd_text(jd_text: str) -> str:
    """
    Sanitize job description text.
    
    Args:
        jd_text: Job description text
    
    Returns:
        Sanitized JD text
    """
    return sanitize_text(jd_text, max_length=MAX_JD_LENGTH, allow_html=False)


def sanitize_resume_text(resume_text: str) -> str:
    """
    Sanitize resume text.
    
    Args:
        resume_text: Resume text
    
    Returns:
        Sanitized resume text
    """
    return sanitize_text(resume_text, max_length=MAX_TEXT_LENGTH, allow_html=False)


# ============================================================
# File Content Validation
# ============================================================

def validate_file_content(file_obj, expected_type: str, max_size: int) -> bool:
    """
    Validate file content beyond magic bytes.
    
    Args:
        file_obj: File object
        expected_type: Expected file type ('pdf', 'docx', 'txt')
        max_size: Maximum file size in bytes
    
    Returns:
        True if file is valid
    
    Raises:
        ValueError: If file is invalid or dangerous
    """
    current_pos = file_obj.tell()
    
    try:
        # Check file size
        file_obj.seek(0, 2)  # Seek to end
        file_size = file_obj.tell()
        file_obj.seek(current_pos)  # Reset
        
        if file_size > max_size:
            raise ValueError(f"File size ({file_size} bytes) exceeds maximum ({max_size} bytes)")
        
        if file_size == 0:
            raise ValueError("File is empty")
        
        # Read first bytes for magic byte validation
        file_obj.seek(0)
        header = file_obj.read(min(1024, file_size))
        file_obj.seek(current_pos)  # Reset
        
        if expected_type == 'pdf':
            if not header.startswith(b'%PDF'):
                raise ValueError("File does not appear to be a valid PDF")
            # Check PDF version
            if b'%PDF-' not in header[:20]:
                raise ValueError("Invalid PDF header")
        
        elif expected_type == 'docx':
            if not header.startswith(b'PK\x03\x04'):
                raise ValueError("File does not appear to be a valid DOCX (ZIP) file")
            # DOCX files should contain word/ directory in ZIP
            # Basic validation - more thorough validation happens during extraction
        
        elif expected_type == 'txt':
            # Try to decode as UTF-8
            try:
                header.decode('utf-8')
            except UnicodeDecodeError:
                raise ValueError("Text file is not valid UTF-8")
            
            # Check for null bytes (shouldn't be in text files)
            if b'\x00' in header:
                raise ValueError("Text file contains null bytes (potentially binary file)")
        
        return True
        
    except ValueError:
        raise
    except Exception as e:
        logger.error(f"File validation error: {e}", exc_info=True)
        raise ValueError(f"File validation failed: {str(e)}")
    finally:
        file_obj.seek(current_pos)


def validate_file_path(file_path: str, base_dir: Optional[str] = None) -> str:
    """
    Validate and sanitize file path to prevent path traversal.
    
    Args:
        file_path: File path to validate
        base_dir: Base directory to restrict paths to (optional)
    
    Returns:
        Normalized, validated path
    
    Raises:
        ValueError: If path is invalid or attempts path traversal
    """
    # Normalize path
    normalized = os.path.normpath(file_path)
    
    # Check for path traversal
    if '..' in normalized or normalized.startswith('/'):
        raise ValueError("Path traversal detected in file path")
    
    # If base_dir is provided, ensure path is within it
    if base_dir:
        base_path = os.path.normpath(base_dir)
        full_path = os.path.normpath(os.path.join(base_path, normalized))
        
        if not full_path.startswith(base_path):
            raise ValueError("File path is outside allowed directory")
        
        return full_path
    
    return normalized


# ============================================================
# Input Validation Helpers
# ============================================================

def validate_user_id(user_id: str) -> str:
    """
    Validate and sanitize user ID.
    
    Args:
        user_id: User ID string
    
    Returns:
        Sanitized user ID
    
    Raises:
        ValueError: If user ID is invalid
    """
    if not user_id:
        raise ValueError("User ID cannot be empty")
    
    # User IDs should be alphanumeric with hyphens/underscores
    if not re.match(r'^[a-zA-Z0-9_-]+$', user_id):
        raise ValueError("User ID contains invalid characters")
    
    if len(user_id) > 100:
        raise ValueError("User ID exceeds maximum length")
    
    return user_id


def validate_job_id(job_id: str) -> str:
    """
    Validate and sanitize job ID (UUID format).
    
    Args:
        job_id: Job ID string
    
    Returns:
        Sanitized job ID
    
    Raises:
        ValueError: If job ID is invalid
    """
    if not job_id:
        raise ValueError("Job ID cannot be empty")
    
    # UUID format: 8-4-4-4-12 hex digits
    uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    if not re.match(uuid_pattern, job_id, re.IGNORECASE):
        raise ValueError("Invalid job ID format (must be UUID)")
    
    return job_id.lower()


def validate_tags(tags: str) -> List[str]:
    """
    Validate and sanitize tags (comma-separated).
    
    Args:
        tags: Comma-separated tags string
    
    Returns:
        List of sanitized tags
    
    Raises:
        ValueError: If tags are invalid
    """
    if not tags:
        return []
    
    # Split and sanitize each tag
    tag_list = [tag.strip() for tag in tags.split(',')]
    sanitized_tags = []
    
    for tag in tag_list:
        if not tag:
            continue
        
        # Tags should be alphanumeric with spaces, hyphens, underscores
        if not re.match(r'^[a-zA-Z0-9\s_-]+$', tag):
            logger.warning(f"Invalid tag format: {tag}")
            continue
        
        if len(tag) > 50:
            logger.warning(f"Tag too long: {tag}")
            continue
        
        sanitized_tags.append(tag)
    
    # Limit number of tags
    if len(sanitized_tags) > 20:
        raise ValueError("Maximum 20 tags allowed")
    
    return sanitized_tags


def validate_persona(persona: str) -> str:
    """
    Validate recruiter persona.
    
    Args:
        persona: Persona string
    
    Returns:
        Validated persona
    
    Raises:
        ValueError: If persona is invalid
    """
    allowed_personas = ["general", "technical", "hr", "executive", "startup"]
    
    if persona not in allowed_personas:
        raise ValueError(f"Invalid persona. Allowed values: {', '.join(allowed_personas)}")
    
    return persona


# ============================================================
# SQL Injection Prevention (Extra Layer)
# ============================================================

def is_safe_for_sql(text: str) -> bool:
    """
    Check if text is safe for SQL queries (extra validation layer).
    
    Note: SQLAlchemy already prevents SQL injection, but this adds
    an extra validation layer for user inputs.
    
    Args:
        text: Text to validate
    
    Returns:
        True if text appears safe
    """
    if not isinstance(text, str):
        return False
    
    # Check for SQL injection patterns
    for pattern in SQL_INJECTION_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return False
    
    return True


# ============================================================
# Rate Limiting Input Validation
# ============================================================

def validate_input_length(text: str, field_name: str, max_length: int) -> str:
    """
    Validate input length for a specific field.
    
    Args:
        text: Input text
        field_name: Name of the field (for error messages)
        max_length: Maximum allowed length
    
    Returns:
        Validated text
    
    Raises:
        ValueError: If text exceeds max length
    """
    if len(text) > max_length:
        raise ValueError(f"{field_name} exceeds maximum length of {max_length} characters")
    
    return text

