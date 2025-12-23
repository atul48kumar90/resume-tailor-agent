# Test Scripts

This directory contains test scripts for the Resume Tailor Agent API.

## Prerequisites

1. **API Server Running**: The API must be running before executing tests
   
   **Quick Start (Recommended)**:
   ```bash
   cd scripts
   ./start_api.sh
   ```
   
   Or manually:
   ```bash
   uvicorn api.main:app --reload
   ```

2. **Dependencies**: 
   - `curl` - For making HTTP requests
   - `jq` (optional) - For JSON parsing and validation
   - `bash` - Shell interpreter
   - `python` with `uvicorn` - For running the API
   - `redis` (optional but recommended) - For resume management and versioning

## Scripts

### Configuration
- `test_config.sh` - Shared configuration and helper functions

### Individual Feature Tests
- `test_visual_comparison.sh` - Tests visual before/after comparison
- `test_skill_gap.sh` - Tests skill gap analysis
- `test_batch_processing.sh` - Tests batch processing for multiple JDs
- `test_ats_validation.sh` - Tests ATS format validation
- `test_resume_management.sh` - Tests resume management dashboard
- `test_versioning_ui.sh` - Tests Resume Versioning UI (list versions, get version, compare versions)

### End-to-End Test
- `test_e2e.sh` - Runs all test scripts in sequence
- `test_all_endpoints.sh` - Comprehensive test of all API endpoints (33+ endpoints)

### Utility Scripts
- `start_api.sh` - Start the API server with proper configuration (auto-installs dependencies)
- `install_dependencies.sh` - Install all Python dependencies from requirements.txt
- `start_services.sh` - Start Redis and API server together
- `check_dependencies.sh` - Check if all dependencies are installed
- `quick_test.sh` - Quick smoke test for basic functionality

## Quick Start

### 1. Install Dependencies (First Time Only)
```bash
cd scripts
./install_dependencies.sh
```

Or manually:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Start the API Server
```bash
cd scripts
./start_api.sh
```

This will:
- Check for virtual environment (creates one if missing)
- Check and install missing dependencies automatically (sqlalchemy, asyncpg, etc.)
- Load environment variables from `.env`
- Check Redis connectivity
- Start the API server on http://localhost:8000

### 3. Run Tests
In a new terminal:
```bash
cd scripts
./quick_test.sh        # Quick smoke test
# OR
./test_e2e.sh          # Full test suite
```

## Usage

### Run All Tests (Recommended)
```bash
cd scripts
chmod +x *.sh
./test_e2e.sh
```

### Run Individual Tests
```bash
cd scripts
chmod +x test_visual_comparison.sh
./test_visual_comparison.sh
```

### Configuration

Set environment variables to customize test behavior:

```bash
# Change API URL (default: http://localhost:8000)
export API_BASE_URL=http://localhost:8080

# Change test data directory (default: ./test_data)
export TEST_DATA_DIR=./my_test_data

# Run tests
./test_e2e.sh
```

## Test Data

Test scripts automatically create sample test files:
- `sample_resume.txt` - Sample resume
- `sample_jd.txt` - Sample job description
- `sample_jd2.txt` - Second JD for batch testing
- `sample_jd3.txt` - Third JD for batch testing

These are created in the `test_data` directory (or `$TEST_DATA_DIR` if set).

## Output

Each test script:
- Prints colored output (green for pass, red for fail)
- Saves JSON responses to `test_data/` directory
- Provides summary statistics at the end

## Troubleshooting

### API Not Running
```
Error: API is not reachable
```
**Solution**: Start the API server first
```bash
cd scripts
./start_api.sh
```

Or manually:
```bash
# Activate virtual environment (if using one)
source .venv/bin/activate

# Load environment variables
export OPENAI_API_KEY=your_key_here

# Start server
uvicorn api.main:app --reload
```

### Permission Denied
```
bash: ./test_e2e.sh: Permission denied
```
**Solution**: Make scripts executable
```bash
chmod +x scripts/*.sh
```

### jq Not Found
Tests will still run but JSON validation will be skipped. Install jq:
```bash
# macOS
brew install jq

# Ubuntu/Debian
sudo apt-get install jq

# CentOS/RHEL
sudo yum install jq
```

### Redis Connection Issues
Some features require Redis. Ensure Redis is running:
```bash
redis-server
```

## Test Coverage

### Visual Comparison
- ✅ Response includes visual_comparison
- ✅ Structure validation (summary, experience, skills, text_diff)
- ✅ Statistics validation

### Skill Gap Analysis
- ✅ Response includes skill_gap_analysis
- ✅ Missing skills detection
- ✅ Recommendations generation
- ✅ Gap severity calculation

### Batch Processing
- ✅ Multiple JD processing
- ✅ Results structure validation
- ✅ Best/worst match identification
- ✅ Summary statistics

### ATS Format Validation
- ✅ File type validation
- ✅ Response structure validation
- ✅ Score calculation
- ✅ Issues and recommendations

### Resume Management
- ✅ Resume CRUD operations
- ✅ Application tracking
- ✅ Status updates
- ✅ Dashboard statistics

### Resume Versioning UI
- ✅ List resume versions endpoint
- ✅ Get specific version endpoint
- ✅ Compare versions endpoint (with compare_with parameter)
- ✅ Compare with current version (without compare_with)
- ✅ Response structure validation (version metadata, comparison, side_by_side, statistics)
- ✅ Error handling (invalid UUID, non-existent version)
- ✅ All resume sections included in comparison (summary, experience, skills, education, certifications, projects, languages, awards, contact)

### API Analytics
- ✅ Usage statistics endpoint
- ✅ Top endpoints endpoint
- ✅ Endpoint-specific analytics
- ✅ Usage summary endpoint

## Test All Endpoints

To test all API endpoints comprehensively:

```bash
cd scripts
./test_all_endpoints.sh
```

This script tests 33+ endpoints including:
- Health check
- Resume parsing (file and text)
- Resume tailoring (text and files)
- Job status and queue stats
- ATS comparison
- Batch processing (file and text)
- Skill gap analysis
- Resume management (CRUD)
- Application tracking
- Dashboard
- Visual comparison
- ATS format validation
- Resume download (multiple formats)
- Templates (list, get, customize, preview)
- PDF/ZIP download
- Resume versioning (list, get, compare)
- Analytics (usage, top, endpoint, summary)

## Continuous Testing

For continuous testing during development:

```bash
# Watch for changes and run tests
while true; do
    ./test_e2e.sh
    sleep 30
done
```

Or use a file watcher:
```bash
# Install entr (macOS: brew install entr)
find . -name "*.py" | entr -c ./test_e2e.sh
```

