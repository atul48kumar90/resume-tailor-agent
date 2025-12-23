# File Upload Security Guide

This document describes the comprehensive file upload security measures implemented in the Resume Tailor Agent.

## Security Layers

### 1. Virus/Malware Scanning

#### ClamAV Integration

The application supports ClamAV for virus scanning:

**Setup:**
```bash
# Install ClamAV
# macOS
brew install clamav

# Ubuntu/Debian
sudo apt-get install clamav clamav-daemon

# Start ClamAV daemon
sudo systemctl start clamav-daemon
```

**Configuration:**
```bash
# .env
ENABLE_VIRUS_SCAN=true
CLAMAV_SOCKET=/var/run/clamav/clamd.ctl
```

**Behavior:**
- If ClamAV is available, files are scanned before processing
- If ClamAV is not available, the application continues with heuristic checks
- Graceful degradation ensures the application works even without ClamAV

#### Heuristic Scanning

Lightweight pattern-based detection that works without ClamAV:

- **Executable Detection**: Detects PE, ELF, Mach-O executables
- **Script Detection**: Detects shell scripts and embedded scripts
- **Suspicious Patterns**: Detects JavaScript, eval(), system() calls
- **Entropy Analysis**: Detects high-entropy files (potential encryption/compression)

### 2. Enhanced Content-Type Validation

#### Magic Bytes Validation

Files are validated using magic bytes (file signatures):

- **PDF**: Must start with `%PDF`
- **DOCX**: Must start with `PK\x03\x04` (ZIP signature)
- **TXT**: Must be valid UTF-8 with no null bytes

#### MIME Type Detection

Uses `python-magic` library for MIME type detection:

- **PDF**: `application/pdf`
- **DOCX**: `application/vnd.openxmlformats-officedocument.wordprocessingml.document`
- **TXT**: `text/plain` or `text/utf-8`

**Fallback:**
If `python-magic` is not available, falls back to Python's `mimetypes` module.

### 3. User Tier-Based File Size Limits

Different file size limits based on user tier:

| Tier | Max File Size | Use Case |
|------|---------------|----------|
| Free | 5 MB | Basic users |
| Premium | 20 MB | Power users |
| Enterprise | 50 MB | Business users |

**Configuration:**
```python
from core.file_security import get_max_file_size_for_tier

max_size = get_max_file_size_for_tier("premium")  # Returns 20 * 1024 * 1024
```

## Security Check Flow

```
1. Filename Sanitization
   ↓
2. File Size Check (tier-based)
   ↓
3. Magic Bytes Validation
   ↓
4. MIME Type Validation
   ↓
5. Virus Scanning (ClamAV + Heuristics)
   ↓
6. Content Validation
   ↓
7. File Processing
```

## Usage Examples

### Basic File Upload

```python
from api.files import extract_text
from core.file_security import validate_file_security

# File is automatically validated during extraction
text = extract_text(uploaded_file)
```

### Custom User Tier

```python
from api.files import extract_text

# Set user tier on file object
uploaded_file.user_tier = "premium"
text = extract_text(uploaded_file)  # Uses 20MB limit
```

### Manual Security Check

```python
from core.file_security import validate_file_security
import tempfile

# Save uploaded file temporarily
with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
    tmp.write(uploaded_file.read())
    temp_path = tmp.name

# Validate security
is_safe, error, details = validate_file_security(
    temp_path,
    expected_type="pdf",
    user_tier="free",
    file_size=file_size
)

if not is_safe:
    raise ValueError(error)
```

## Security Details Response

The security validation returns detailed information:

```python
{
    "size_check": "passed",
    "content_type_check": "passed",
    "virus_scan": {
        "clamav_available": true,
        "clamav_result": "clean",
        "heuristic_result": "clean",
        "threats_detected": []
    }
}
```

## Configuration

### Environment Variables

```bash
# Enable/disable virus scanning
ENABLE_VIRUS_SCAN=true

# Enable/disable heuristic scanning
ENABLE_HEURISTIC_SCAN=true

# ClamAV socket path
CLAMAV_SOCKET=/var/run/clamav/clamd.ctl
```

### Disabling Security Checks

**Not Recommended**, but possible for development:

```bash
ENABLE_VIRUS_SCAN=false
ENABLE_HEURISTIC_SCAN=false
```

## Threat Detection

### Detected Threats

1. **Executable Files**: PE, ELF, Mach-O executables
2. **Shell Scripts**: Files starting with `#!/bin/` or `#!/usr/bin/`
3. **Embedded Scripts**: JavaScript, eval(), exec(), system() calls
4. **Malware**: Detected by ClamAV signature database
5. **Suspicious Patterns**: High entropy, unusual file structures

### Response to Threats

When a threat is detected:

1. File upload is **rejected**
2. Error message is returned to user
3. Threat is **logged** for security monitoring
4. File is **not processed** or stored

## Performance Considerations

### Virus Scanning

- **ClamAV Daemon**: Fast (uses daemon socket)
- **ClamAV Standalone**: Slower (spawns process)
- **Heuristic Scan**: Very fast (pattern matching)

### Optimization

- Only files < 10MB are scanned with ClamAV (configurable)
- Heuristic scans check first 1MB only
- Large files skip full virus scan but still validated

## Best Practices

1. **Always Enable Virus Scanning in Production**
   ```bash
   ENABLE_VIRUS_SCAN=true
   ```

2. **Keep ClamAV Updated**
   ```bash
   sudo freshclam  # Update virus definitions
   ```

3. **Monitor Security Logs**
   - Check logs for detected threats
   - Review security_details in responses

4. **Set Appropriate User Tiers**
   - Default to 'free' tier for new users
   - Upgrade users based on subscription

5. **Handle Security Errors Gracefully**
   - Don't expose internal security details to users
   - Log detailed information for administrators

## Troubleshooting

### ClamAV Not Found

**Symptom**: Warning "ClamAV not found, skipping virus scan"

**Solution**: 
- Install ClamAV: `brew install clamav` (macOS) or `apt-get install clamav` (Linux)
- Or disable virus scanning: `ENABLE_VIRUS_SCAN=false`

### python-magic Import Error

**Symptom**: Warning "MIME type detection failed"

**Solution**:
- Install python-magic: `pip install python-magic`
- On macOS: `brew install libmagic`
- On Linux: `apt-get install libmagic1`
- Application will fallback to mimetypes module

### File Size Limit Errors

**Symptom**: "File size exceeds maximum allowed size for X tier"

**Solution**:
- Upgrade user tier
- Reduce file size
- Or adjust tier limits in `core/file_security.py`

## Security Checklist

When deploying:

- [ ] ClamAV installed and running
- [ ] Virus definitions updated (`freshclam`)
- [ ] `ENABLE_VIRUS_SCAN=true` in production
- [ ] `ENABLE_HEURISTIC_SCAN=true` in production
- [ ] User tiers properly configured
- [ ] Security logs monitored
- [ ] File size limits appropriate for use case

