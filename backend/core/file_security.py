# core/file_security.py
"""
File upload security module.

Provides:
- Virus/malware scanning (ClamAV integration)
- Enhanced content-type validation
- File size limits per user tier
- Malicious file pattern detection
"""
import os
import logging
import subprocess
import tempfile
from typing import Optional, Tuple, Dict, Any
from pathlib import Path

# Try to import python-magic, fallback to mimetypes if not available
try:
    import magic
    MAGIC_AVAILABLE = True
except ImportError:
    MAGIC_AVAILABLE = False
    import mimetypes

from core.settings import ENABLE_VIRUS_SCAN, ENABLE_HEURISTIC_SCAN

logger = logging.getLogger(__name__)

# User tiers and their file size limits (in MB)
USER_TIER_LIMITS = {
    "free": 5,      # 5MB for free users
    "premium": 20,  # 20MB for premium users
    "enterprise": 50,  # 50MB for enterprise users
}

# Default tier if not specified
DEFAULT_TIER = "free"
DEFAULT_MAX_SIZE_MB = USER_TIER_LIMITS[DEFAULT_TIER]


# ============================================================
# Virus Scanning
# ============================================================

def scan_file_with_clamav(file_path: str) -> Tuple[bool, Optional[str]]:
    """
    Scan file for viruses using ClamAV.
    
    Returns (True, None) if ClamAV is not available (graceful degradation).
    """
    if not ENABLE_VIRUS_SCAN:
        return True, None
    """
    Scan file for viruses using ClamAV.
    
    Args:
        file_path: Path to file to scan
    
    Returns:
        Tuple of (is_safe, threat_name)
        - is_safe: True if file is safe, False if threat detected
        - threat_name: Name of threat if detected, None otherwise
    """
    try:
        # Check if ClamAV is installed
        result = subprocess.run(
            ["clamdscan", "--version"],
            capture_output=True,
            timeout=5
        )
        
        if result.returncode != 0:
            # Try alternative command
            result = subprocess.run(
                ["clamscan", "--version"],
                capture_output=True,
                timeout=5
            )
            if result.returncode != 0:
                logger.warning("ClamAV not found, skipping virus scan")
                return True, None  # Safe by default if ClamAV not available
        
        # Scan file using clamdscan (daemon) or clamscan (standalone)
        scan_cmd = None
        if os.path.exists("/var/run/clamav/clamd.ctl") or os.path.exists("/tmp/clamd.sock"):
            # Use daemon if available (faster)
            scan_cmd = ["clamdscan", "--no-summary", file_path]
        else:
            # Use standalone scanner
            scan_cmd = ["clamscan", "--no-summary", "--infected", file_path]
        
        result = subprocess.run(
            scan_cmd,
            capture_output=True,
            text=True,
            timeout=30  # 30 second timeout for scanning
        )
        
        # ClamAV returns 0 if clean, 1 if infected
        if result.returncode == 1:
            # Extract threat name from output
            threat_name = result.stdout.strip() or "Unknown threat"
            logger.warning(f"Virus detected in file {file_path}: {threat_name}")
            return False, threat_name
        
        # Return code 0 means file is clean
        logger.info(f"File {file_path} passed ClamAV scan")
        return True, None
        
    except subprocess.TimeoutExpired:
        logger.error(f"ClamAV scan timeout for {file_path}")
        # On timeout, we'll allow the file but log the issue
        return True, None
    except FileNotFoundError:
        logger.warning("ClamAV not installed, skipping virus scan")
        return True, None  # Safe by default if ClamAV not available
    except Exception as e:
        logger.error(f"Error scanning file with ClamAV: {e}", exc_info=True)
        # On error, we'll allow the file but log the issue
        return True, None


def detect_suspicious_patterns(file_content: bytes, filename: str) -> Tuple[bool, Optional[str]]:
    """
    Detect suspicious patterns in file content (heuristic-based).
    
    Returns (True, None) if heuristic scanning is disabled.
    """
    if not ENABLE_HEURISTIC_SCAN:
        return True, None
    """
    Detect suspicious patterns in file content (heuristic-based).
    
    This is a lightweight check that doesn't require ClamAV.
    Detects common malware patterns and suspicious file structures.
    
    Args:
        file_content: File content bytes
        filename: Original filename
    
    Returns:
        Tuple of (is_safe, threat_description)
    """
    # Check for executable signatures
    executable_signatures = [
        b'MZ\x90\x00',  # PE executable (Windows)
        b'\x7fELF',     # ELF executable (Linux)
        b'\xfe\xed\xfa',  # Mach-O executable (macOS)
        b'#!/bin/',     # Shell script
        b'#!/usr/bin/', # Shell script
    ]
    
    for sig in executable_signatures:
        if file_content.startswith(sig):
            logger.warning(f"Executable file detected: {filename}")
            return False, f"Executable file detected (signature: {sig[:4]})"
    
    # Check for embedded scripts in PDF/DOCX
    suspicious_patterns = [
        b'<script',      # JavaScript in documents
        b'javascript:',  # JavaScript URLs
        b'eval(',        # JavaScript eval
        b'exec(',        # Python exec
        b'system(',      # System calls
    ]
    
    # Only check first 1MB to avoid performance issues
    content_to_check = file_content[:1024 * 1024]
    
    for pattern in suspicious_patterns:
        if pattern in content_to_check:
            logger.warning(f"Suspicious pattern detected in {filename}: {pattern}")
            return False, f"Suspicious script pattern detected: {pattern.decode('utf-8', errors='ignore')}"
    
    # Check for unusually high entropy (potential encrypted/compressed malware)
    if len(file_content) > 1024:
        entropy = _calculate_entropy(file_content[:1024])
        if entropy > 7.5:  # High entropy threshold
            # This might be encrypted/compressed, but not necessarily malicious
            # We'll log it but allow it (PDFs and DOCX files are compressed)
            logger.debug(f"High entropy detected in {filename}: {entropy:.2f}")
    
    return True, None


def _calculate_entropy(data: bytes) -> float:
    """Calculate Shannon entropy of data."""
    if not data:
        return 0.0
    
    import math
    from collections import Counter
    
    counts = Counter(data)
    length = len(data)
    entropy = 0.0
    
    for count in counts.values():
        probability = count / length
        if probability > 0:
            entropy -= probability * math.log2(probability)
    
    return entropy


def scan_file(file_path: str, file_content: Optional[bytes] = None) -> Tuple[bool, Optional[str], Dict[str, Any]]:
    """
    Comprehensive file scanning combining ClamAV and heuristic checks.
    
    Args:
        file_path: Path to file to scan
        file_content: Optional file content bytes (for heuristic checks)
    
    Returns:
        Tuple of (is_safe, threat_name, scan_details)
        - is_safe: True if file is safe
        - threat_name: Name of threat if detected
        - scan_details: Dictionary with scan results
    """
    scan_details = {
        "clamav_available": False,
        "clamav_result": None,
        "heuristic_result": None,
        "threats_detected": [],
    }
    
    # Try ClamAV first (most reliable)
    clamav_safe, clamav_threat = scan_file_with_clamav(file_path)
    scan_details["clamav_available"] = clamav_threat is not None or clamav_safe
    scan_details["clamav_result"] = "clean" if clamav_safe else "infected"
    
    if not clamav_safe:
        scan_details["threats_detected"].append(clamav_threat or "Unknown threat")
        return False, clamav_threat, scan_details
    
    # Fallback to heuristic checks if ClamAV not available or for extra validation
    if file_content is None:
        try:
            with open(file_path, 'rb') as f:
                file_content = f.read()
        except Exception as e:
            logger.error(f"Error reading file for heuristic scan: {e}")
            file_content = b''
    
    heuristic_safe, heuristic_threat = detect_suspicious_patterns(file_content, os.path.basename(file_path))
    scan_details["heuristic_result"] = "clean" if heuristic_safe else "suspicious"
    
    if not heuristic_safe:
        scan_details["threats_detected"].append(heuristic_threat or "Suspicious pattern")
        return False, heuristic_threat, scan_details
    
    return True, None, scan_details


# ============================================================
# Enhanced Content-Type Validation
# ============================================================

def detect_mime_type(file_path: str, file_content: Optional[bytes] = None) -> Optional[str]:
    """
    Detect MIME type using python-magic library or mimetypes fallback.
    
    Args:
        file_path: Path to file
        file_content: Optional file content bytes
    
    Returns:
        MIME type string or None if detection fails
    """
    if MAGIC_AVAILABLE:
        try:
            if file_content:
                # Use content-based detection
                mime = magic.Magic(mime=True)
                return mime.from_buffer(file_content[:1024])  # Check first 1KB
            else:
                # Use file-based detection
                mime = magic.Magic(mime=True)
                return mime.from_file(file_path)
        except Exception as e:
            logger.warning(f"MIME type detection failed: {e}")
    
    # Fallback to mimetypes module
    try:
        mime_type, _ = mimetypes.guess_type(file_path)
        return mime_type
    except Exception as e:
        logger.warning(f"MIME type detection fallback failed: {e}")
        return None


def validate_content_type(
    file_path: str,
    expected_type: str,
    file_content: Optional[bytes] = None
) -> Tuple[bool, Optional[str]]:
    """
    Validate file content type using both magic bytes and MIME type detection.
    
    Args:
        file_path: Path to file
        expected_type: Expected file type ('pdf', 'docx', 'txt')
        file_content: Optional file content bytes
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Expected MIME types
    expected_mimes = {
        'pdf': ['application/pdf'],
        'docx': [
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/zip',  # DOCX is a ZIP file
        ],
        'txt': ['text/plain', 'text/utf-8'],
    }
    
    # Detect MIME type
    detected_mime = detect_mime_type(file_path, file_content)
    
    if detected_mime:
        expected = expected_mimes.get(expected_type, [])
        if detected_mime not in expected:
            # For DOCX, also check if it's a ZIP with word/ directory
            if expected_type == 'docx' and detected_mime == 'application/zip':
                # Additional validation happens during extraction
                return True, None
            
            return False, f"MIME type mismatch: expected {expected}, got {detected_mime}"
    
    # Fallback to magic bytes validation (already implemented in files.py)
    return True, None


# ============================================================
# User Tier-Based File Size Limits
# ============================================================

def get_max_file_size_for_tier(user_tier: str = DEFAULT_TIER) -> int:
    """
    Get maximum file size in bytes for a user tier.
    
    Args:
        user_tier: User tier ('free', 'premium', 'enterprise')
    
    Returns:
        Maximum file size in bytes
    """
    max_size_mb = USER_TIER_LIMITS.get(user_tier, USER_TIER_LIMITS[DEFAULT_TIER])
    return max_size_mb * 1024 * 1024


def validate_file_size(file_size: int, user_tier: str = DEFAULT_TIER) -> Tuple[bool, Optional[str]]:
    """
    Validate file size against user tier limits.
    
    Args:
        file_size: File size in bytes
        user_tier: User tier ('free', 'premium', 'enterprise')
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    max_size = get_max_file_size_for_tier(user_tier)
    
    if file_size > max_size:
        max_size_mb = max_size / (1024 * 1024)
        file_size_mb = file_size / (1024 * 1024)
        return False, (
            f"File size ({file_size_mb:.2f} MB) exceeds maximum allowed size "
            f"({max_size_mb:.2f} MB) for {user_tier} tier. "
            f"Please upgrade your account or reduce file size."
        )
    
    return True, None


# ============================================================
# Comprehensive File Security Check
# ============================================================

def validate_file_security(
    file_path: str,
    expected_type: str,
    user_tier: str = DEFAULT_TIER,
    file_content: Optional[bytes] = None,
    file_size: Optional[int] = None
) -> Tuple[bool, Optional[str], Dict[str, Any]]:
    """
    Comprehensive file security validation.
    
    Performs:
    1. File size validation (tier-based)
    2. Content-type validation (MIME + magic bytes)
    3. Virus scanning (ClamAV + heuristics)
    
    Args:
        file_path: Path to file
        expected_type: Expected file type ('pdf', 'docx', 'txt')
        user_tier: User tier for size limits
        file_content: Optional file content bytes
        file_size: Optional file size in bytes
    
    Returns:
        Tuple of (is_safe, error_message, security_details)
    """
    security_details = {
        "size_check": None,
        "content_type_check": None,
        "virus_scan": None,
        "threats_detected": [],
    }
    
    # 1. File size validation
    if file_size is None:
        try:
            file_size = os.path.getsize(file_path)
        except Exception as e:
            return False, f"Could not determine file size: {str(e)}", security_details
    
    size_valid, size_error = validate_file_size(file_size, user_tier)
    security_details["size_check"] = "passed" if size_valid else "failed"
    if not size_valid:
        return False, size_error, security_details
    
    # 2. Content-type validation
    content_valid, content_error = validate_content_type(file_path, expected_type, file_content)
    security_details["content_type_check"] = "passed" if content_valid else "failed"
    if not content_valid:
        return False, content_error, security_details
    
    # 3. Virus scanning
    scan_safe, threat, scan_details = scan_file(file_path, file_content)
    security_details["virus_scan"] = scan_details
    if not scan_safe:
        return False, f"File failed security scan: {threat}", security_details
    
    return True, None, security_details

