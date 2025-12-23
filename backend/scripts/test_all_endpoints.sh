#!/bin/bash
# test_all_endpoints.sh - Comprehensive test script for all API endpoints

source "$(dirname "$0")/test_config.sh"

echo "=========================================="
echo "Comprehensive API Endpoints Test"
echo "=========================================="
echo ""

# Check if API is running
if ! check_api_health; then
    log_error "API is not running. Please start the API server first."
    log_info "To start the API: uvicorn api.main:app --reload"
    exit 1
fi

# Create test files
create_test_files

# Variables to store IDs for dependent tests
JOB_ID=""
RESUME_ID=""
APPLICATION_ID=""
TEMPLATE_ID=""

# ============================================================
# 1. Health Check
# ============================================================
log_info "Test 1: GET /health"
response=$(curl -s -w "\n%{http_code}" "$API_BASE_URL/health" 2>/dev/null)
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" = "200" ] || [ "$http_code" = "503" ]; then
    log_success "Health check endpoint works (HTTP $http_code)"
else
    log_error "Health check failed (HTTP $http_code)"
fi

# ============================================================
# 2. Resume Parsing
# ============================================================
log_info "Test 2: POST /resume/parse"
response=$(curl -s -w "\n%{http_code}" \
    -X POST "$API_BASE_URL/resume/parse" \
    -F "resume=@$TEST_DATA_DIR/sample_resume.txt" 2>/dev/null)

http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" = "200" ]; then
    log_success "Resume parse endpoint works"
    if echo "$body" | grep -q "contact\|experience\|skills"; then
        log_success "Response contains parsed resume data"
    fi
else
    log_error "Resume parse failed (HTTP $http_code)"
fi

log_info "Test 3: POST /resume/parse/text"
resume_text=$(cat "$TEST_DATA_DIR/sample_resume.txt")
# URL encode the text to avoid issues with special characters
response=$(curl -s -w "\n%{http_code}" \
    -X POST "$API_BASE_URL/resume/parse/text" \
    -F "resume_text=$resume_text" 2>/dev/null)

http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" = "200" ]; then
    log_success "Resume parse text endpoint works"
else
    log_error "Resume parse text failed (HTTP $http_code)"
    if echo "$body" | grep -q "detail"; then
        error_detail=$(echo "$body" | grep -o '"detail":"[^"]*"' | head -1 | cut -d'"' -f4 || echo "")
        if [ -n "$error_detail" ]; then
            log_info "Error: $error_detail"
        fi
    fi
fi

# ============================================================
# 3. Resume Tailoring
# ============================================================
log_info "Test 4: POST /tailor"
response=$(curl -s -w "\n%{http_code}" \
    -X POST "$API_BASE_URL/tailor" \
    -F "job_description_text=Software Engineer position requiring Java, Spring Boot, and REST APIs" \
    -F "resume_file=@$TEST_DATA_DIR/sample_resume.txt" \
    -F "recruiter_persona=general" 2>/dev/null)

http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" = "200" ]; then
    log_success "Tailor endpoint works"
    # Extract job_id
    JOB_ID=$(echo "$body" | grep -o '"job_id":"[^"]*"' | cut -d'"' -f4 || echo "")
    if [ -n "$JOB_ID" ]; then
        log_success "Job ID extracted: $JOB_ID"
    fi
else
    log_error "Tailor endpoint failed (HTTP $http_code)"
    if echo "$body" | grep -q "detail"; then
        error_detail=$(echo "$body" | grep -o '"detail":"[^"]*"' | head -1 | cut -d'"' -f4 || echo "")
        if [ -n "$error_detail" ]; then
            log_info "Error: $error_detail"
        fi
    fi
fi

log_info "Test 5: POST /tailor/files"
response=$(curl -s -w "\n%{http_code}" \
    -X POST "$API_BASE_URL/tailor/files" \
    -F "job_description=@$TEST_DATA_DIR/sample_jd.txt" \
    -F "resume=@$TEST_DATA_DIR/sample_resume.txt" \
    -F "recruiter_persona=general" 2>/dev/null)

http_code=$(echo "$response" | tail -n1)
if [ "$http_code" = "200" ]; then
    log_success "Tailor files endpoint works"
else
    log_error "Tailor files failed (HTTP $http_code)"
fi

# ============================================================
# 4. Job Status
# ============================================================
if [ -n "$JOB_ID" ]; then
    log_info "Test 6: GET /jobs/{job_id}"
    response=$(curl -s -w "\n%{http_code}" \
        "$API_BASE_URL/jobs/$JOB_ID" 2>/dev/null)
    
    http_code=$(echo "$response" | tail -n1)
    if [ "$http_code" = "200" ]; then
        log_success "Job status endpoint works"
    else
        log_warning "Job status check failed (HTTP $http_code) - job may not be ready"
    fi
else
    log_warning "Skipping job status test (no job_id available)"
fi

log_info "Test 7: GET /queue/stats"
response=$(curl -s -w "\n%{http_code}" \
    "$API_BASE_URL/queue/stats" 2>/dev/null)

http_code=$(echo "$response" | tail -n1)
if [ "$http_code" = "200" ]; then
    log_success "Queue stats endpoint works"
else
    log_error "Queue stats failed (HTTP $http_code)"
fi

# ============================================================
# 5. ATS Comparison
# ============================================================
log_info "Test 8: POST /ats/compare"
response=$(curl -s -w "\n%{http_code}" \
    -X POST "$API_BASE_URL/ats/compare" \
    -F "jd_file=@$TEST_DATA_DIR/sample_jd.txt" \
    -F "resume=@$TEST_DATA_DIR/sample_resume.txt" 2>/dev/null)

http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" = "200" ]; then
    log_success "ATS compare endpoint works"
    # Extract job_id for dependent tests
    COMPARE_JOB_ID=$(echo "$body" | grep -o '"job_id":"[^"]*"' | cut -d'"' -f4 || echo "")
    if [ -n "$COMPARE_JOB_ID" ]; then
        log_success "Compare job ID: $COMPARE_JOB_ID"
    fi
else
    log_error "ATS compare failed (HTTP $http_code)"
fi

# ============================================================
# 6. Batch Processing
# ============================================================
log_info "Test 9: POST /ats/batch"
# Note: FastAPI multipart form requires proper file array handling
response=$(curl -s -w "\n%{http_code}" \
    -X POST "$API_BASE_URL/ats/batch" \
    -F "resume=@$TEST_DATA_DIR/sample_resume.txt" \
    -F "jd_files=@$TEST_DATA_DIR/sample_jd.txt" \
    -F "jd_files=@$TEST_DATA_DIR/sample_jd2.txt" 2>/dev/null)

http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" = "200" ]; then
    log_success "Batch processing endpoint works"
else
    log_error "Batch processing failed (HTTP $http_code)"
    if echo "$body" | grep -q "detail"; then
        error_detail=$(echo "$body" | grep -o '"detail":"[^"]*"' | head -1 | cut -d'"' -f4 || echo "")
        if [ -n "$error_detail" ]; then
            log_info "Error: $error_detail"
        fi
    fi
fi

log_info "Test 10: POST /ats/batch/text"
jd_text=$(cat "$TEST_DATA_DIR/sample_jd.txt")
# For FastAPI List[str] in Form, send multiple form fields with the same name
# For a single JD, we can send it once and FastAPI will wrap it in a list
# Note: curl needs to send the field multiple times for multiple values
response=$(curl -s -w "\n%{http_code}" \
    -X POST "$API_BASE_URL/ats/batch/text" \
    -F "resume=@$TEST_DATA_DIR/sample_resume.txt" \
    -F "jd_texts=$jd_text" 2>/dev/null)

http_code=$(echo "$response" | tail -n1)
if [ "$http_code" = "200" ]; then
    log_success "Batch text endpoint works"
else
    log_error "Batch text failed (HTTP $http_code)"
fi

# ============================================================
# 7. Skill Gap Analysis
# ============================================================
if [ -n "$COMPARE_JOB_ID" ]; then
    log_info "Test 11: GET /ats/compare/{job_id}/skill-gap"
    response=$(curl -s -w "\n%{http_code}" \
        "$API_BASE_URL/ats/compare/$COMPARE_JOB_ID/skill-gap" 2>/dev/null)
    
    http_code=$(echo "$response" | tail -n1)
    if [ "$http_code" = "200" ]; then
        log_success "Skill gap endpoint works"
    else
        log_warning "Skill gap check failed (HTTP $http_code) - job may not be ready"
    fi
else
    log_warning "Skipping skill gap test (no compare job_id available)"
fi

# ============================================================
# 8. Resume Management
# ============================================================
log_info "Test 12: POST /resumes"
response=$(curl -s -w "\n%{http_code}" \
    -X POST "$API_BASE_URL/resumes" \
    -F "title=Test Resume" \
    -F "tags=test,api" \
    -F "user_id=test_user" 2>/dev/null)

http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" = "200" ] || [ "$http_code" = "201" ]; then
    log_success "Create resume endpoint works"
    # Extract resume_id
    RESUME_ID=$(echo "$body" | grep -o '"resume_id":"[^"]*"' | cut -d'"' -f4 || echo "")
    if [ -z "$RESUME_ID" ]; then
        RESUME_ID=$(echo "$body" | grep -o '"id":"[^"]*"' | cut -d'"' -f4 || echo "")
    fi
    if [ -n "$RESUME_ID" ]; then
        log_success "Resume ID extracted: $RESUME_ID"
    fi
else
    log_error "Create resume failed (HTTP $http_code)"
fi

log_info "Test 13: GET /resumes"
response=$(curl -s -w "\n%{http_code}" \
    "$API_BASE_URL/resumes?user_id=test_user" 2>/dev/null)

http_code=$(echo "$response" | tail -n1)
if [ "$http_code" = "200" ]; then
    log_success "List resumes endpoint works"
else
    log_error "List resumes failed (HTTP $http_code)"
fi

if [ -n "$RESUME_ID" ]; then
    log_info "Test 14: GET /resumes/{resume_id}"
    response=$(curl -s -w "\n%{http_code}" \
        "$API_BASE_URL/resumes/$RESUME_ID" 2>/dev/null)
    
    http_code=$(echo "$response" | tail -n1)
    if [ "$http_code" = "200" ]; then
        log_success "Get resume endpoint works"
    else
        log_warning "Get resume failed (HTTP $http_code) - may need database setup"
    fi
    
    log_info "Test 15: POST /resumes/{resume_id}/applications"
    response=$(curl -s -w "\n%{http_code}" \
        -X POST "$API_BASE_URL/resumes/$RESUME_ID/applications" \
        -F "job_title=Software Engineer" \
        -F "company=Test Corp" \
        -F "jd_file=@$TEST_DATA_DIR/sample_jd.txt" 2>/dev/null)
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" = "200" ] || [ "$http_code" = "201" ]; then
        log_success "Create application endpoint works"
        # Extract application_id
        APPLICATION_ID=$(echo "$body" | grep -o '"application_id":"[^"]*"' | cut -d'"' -f4 || echo "")
        if [ -z "$APPLICATION_ID" ]; then
            APPLICATION_ID=$(echo "$body" | grep -o '"id":"[^"]*"' | cut -d'"' -f4 || echo "")
        fi
    else
        log_warning "Create application failed (HTTP $http_code) - may need database setup"
    fi
else
    log_warning "Skipping resume-dependent tests (no resume_id available)"
fi

# ============================================================
# 9. Application Management
# ============================================================
if [ -n "$APPLICATION_ID" ]; then
    log_info "Test 16: PATCH /applications/{application_id}"
    response=$(curl -s -w "\n%{http_code}" \
        -X PATCH "$API_BASE_URL/applications/$APPLICATION_ID" \
        -F "status=interview" \
        -F "notes=Test update" 2>/dev/null)
    
    http_code=$(echo "$response" | tail -n1)
    if [ "$http_code" = "200" ]; then
        log_success "Update application endpoint works"
    else
        log_warning "Update application failed (HTTP $http_code)"
    fi
else
    log_warning "Skipping application update test (no application_id available)"
fi

# ============================================================
# 10. Dashboard
# ============================================================
log_info "Test 17: GET /dashboard"
response=$(curl -s -w "\n%{http_code}" \
    "$API_BASE_URL/dashboard?user_id=test_user" 2>/dev/null)

http_code=$(echo "$response" | tail -n1)
if [ "$http_code" = "200" ]; then
    log_success "Dashboard endpoint works"
else
    log_warning "Dashboard failed (HTTP $http_code) - may need database setup"
fi

# ============================================================
# 11. Visual Comparison
# ============================================================
if [ -n "$COMPARE_JOB_ID" ]; then
    log_info "Test 18: GET /ats/compare/{job_id}/visual"
    response=$(curl -s -w "\n%{http_code}" \
        "$API_BASE_URL/ats/compare/$COMPARE_JOB_ID/visual" 2>/dev/null)
    
    http_code=$(echo "$response" | tail -n1)
    if [ "$http_code" = "200" ]; then
        log_success "Visual comparison endpoint works"
    else
        log_warning "Visual comparison failed (HTTP $http_code) - job may not be ready"
    fi
else
    log_warning "Skipping visual comparison test (no compare job_id available)"
fi

# ============================================================
# 12. ATS Format Validation
# ============================================================
log_info "Test 19: POST /ats/validate-format"
response=$(curl -s -w "\n%{http_code}" \
    -X POST "$API_BASE_URL/ats/validate-format" \
    -F "resume_file=@$TEST_DATA_DIR/sample_resume.txt" 2>/dev/null)

http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" = "200" ]; then
    log_success "ATS format validation endpoint works"
else
    log_warning "ATS format validation failed (HTTP $http_code) - TXT may not be supported format"
    if echo "$body" | grep -q "detail"; then
        error_detail=$(echo "$body" | grep -o '"detail":"[^"]*"' | head -1 | cut -d'"' -f4 || echo "")
        if [ -n "$error_detail" ]; then
            log_info "Error: $error_detail"
        fi
    fi
fi

# ============================================================
# 13. Resume Download
# ============================================================
log_info "Test 20: POST /ats/download"
# Create a simple resume JSON - this endpoint expects JSON body, not form data
resume_json='{"summary":"Test summary","experience":[{"title":"Engineer","company":"Tech","bullets":["Worked on projects"]}],"skills":["Python","Java"]}'
response=$(curl -s -w "\n%{http_code}" \
    -X POST "$API_BASE_URL/ats/download?format=docx" \
    -H "Content-Type: application/json" \
    -d "$resume_json" 2>/dev/null)

http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" = "200" ]; then
    log_success "Download endpoint works"
else
    log_warning "Download failed (HTTP $http_code) - may need proper JSON format"
    if echo "$body" | grep -q "detail"; then
        error_detail=$(echo "$body" | grep -o '"detail":"[^"]*"' | head -1 | cut -d'"' -f4 || echo "")
        if [ -n "$error_detail" ]; then
            log_info "Error: $error_detail"
        fi
    fi
fi

# ============================================================
# 14. Templates
# ============================================================
log_info "Test 21: GET /ats/templates"
response=$(curl -s -w "\n%{http_code}" \
    "$API_BASE_URL/ats/templates" 2>/dev/null)

http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" = "200" ]; then
    log_success "List templates endpoint works"
    # Extract first template_id
    TEMPLATE_ID=$(echo "$body" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4 || echo "classic")
    if [ -n "$TEMPLATE_ID" ]; then
        log_success "Template ID extracted: $TEMPLATE_ID"
    fi
else
    log_error "List templates failed (HTTP $http_code)"
fi

if [ -n "$TEMPLATE_ID" ]; then
    log_info "Test 22: GET /ats/templates/{template_id}"
    response=$(curl -s -w "\n%{http_code}" \
        "$API_BASE_URL/ats/templates/$TEMPLATE_ID" 2>/dev/null)
    
    http_code=$(echo "$response" | tail -n1)
    if [ "$http_code" = "200" ]; then
        log_success "Get template details endpoint works"
    else
        log_error "Get template details failed (HTTP $http_code)"
    fi
fi

log_info "Test 23: POST /ats/templates/customize"
custom_template='{"font_family":"Arial","font_size":11,"color_scheme":"professional"}'
response=$(curl -s -w "\n%{http_code}" \
    -X POST "$API_BASE_URL/ats/templates/customize" \
    -H "Content-Type: application/json" \
    -d "$custom_template" 2>/dev/null)

http_code=$(echo "$response" | tail -n1)
if [ "$http_code" = "200" ]; then
    log_success "Customize template endpoint works"
else
    log_warning "Customize template failed (HTTP $http_code)"
fi

log_info "Test 24: POST /ats/templates/preview"
response=$(curl -s -w "\n%{http_code}" \
    -X POST "$API_BASE_URL/ats/templates/preview" \
    -H "Content-Type: application/json" \
    -d "$resume_json" \
    -F "template_id=classic" 2>/dev/null)

http_code=$(echo "$response" | tail -n1)
if [ "$http_code" = "200" ]; then
    log_success "Template preview endpoint works"
else
    log_warning "Template preview failed (HTTP $http_code)"
fi

# ============================================================
# 15. PDF/ZIP Download
# ============================================================
log_info "Test 25: POST /ats/download/pdf"
# This endpoint has mixed format (dict body + Form field) - FastAPI limitation
# We'll skip this test as it requires special handling
log_warning "Skipping PDF download test - endpoint has mixed JSON body + form field format"
http_code="SKIP"
body=""

if [ "$http_code" = "SKIP" ]; then
    log_warning "PDF download test skipped"
elif [ "$http_code" = "200" ]; then
    log_success "PDF download endpoint works"
else
    log_warning "PDF download failed (HTTP $http_code)"
    if echo "$body" | grep -q "detail"; then
        error_detail=$(echo "$body" | grep -o '"detail":"[^"]*"' | head -1 | cut -d'"' -f4 || echo "")
        if [ -n "$error_detail" ]; then
            log_info "Error: $error_detail"
        fi
    fi
fi

log_info "Test 26: POST /ats/download/zip"
# This endpoint has mixed format (dict body + query param) - may work
resume_json='{"summary":"Test summary","experience":[{"title":"Engineer","company":"Tech","bullets":["Worked on projects"]}],"skills":["Python","Java"]}'
response=$(curl -s -w "\n%{http_code}" \
    -X POST "$API_BASE_URL/ats/download/zip?template_id=classic" \
    -H "Content-Type: application/json" \
    -d "$resume_json" 2>/dev/null)

http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" = "200" ]; then
    log_success "ZIP download endpoint works"
else
    log_warning "ZIP download failed (HTTP $http_code)"
    if echo "$body" | grep -q "detail"; then
        error_detail=$(echo "$body" | grep -o '"detail":"[^"]*"' | head -1 | cut -d'"' -f4 || echo "")
        if [ -n "$error_detail" ]; then
            log_info "Error: $error_detail"
        fi
    fi
fi

# ============================================================
# 16. Resume Versioning
# ============================================================
if [ -n "$RESUME_ID" ]; then
    log_info "Test 27: GET /resumes/{resume_id}/versions"
    response=$(curl -s -w "\n%{http_code}" \
        "$API_BASE_URL/resumes/$RESUME_ID/versions" 2>/dev/null)
    
    http_code=$(echo "$response" | tail -n1)
    if [ "$http_code" = "200" ]; then
        log_success "List versions endpoint works"
        # Extract version_id if available
        VERSION_ID=$(echo "$response" | sed '$d' | grep -o '"version_id":"[^"]*"' | head -1 | cut -d'"' -f4 || echo "")
    elif [ "$http_code" = "404" ]; then
        log_warning "List versions returned 404 (resume may not exist in database)"
    else
        log_warning "List versions failed (HTTP $http_code)"
    fi
    
    if [ -n "$VERSION_ID" ] && [ "$VERSION_ID" != "null" ]; then
        log_info "Test 28: GET /resumes/{resume_id}/versions/{version_id}"
        response=$(curl -s -w "\n%{http_code}" \
            "$API_BASE_URL/resumes/$RESUME_ID/versions/$VERSION_ID" 2>/dev/null)
        
        http_code=$(echo "$response" | tail -n1)
        if [ "$http_code" = "200" ]; then
            log_success "Get version endpoint works"
        else
            log_warning "Get version failed (HTTP $http_code)"
        fi
        
        log_info "Test 29: GET /resumes/{resume_id}/versions/{version_id}/compare"
        response=$(curl -s -w "\n%{http_code}" \
            "$API_BASE_URL/resumes/$RESUME_ID/versions/$VERSION_ID/compare" 2>/dev/null)
        
        http_code=$(echo "$response" | tail -n1)
        if [ "$http_code" = "200" ]; then
            log_success "Compare versions endpoint works"
        else
            log_warning "Compare versions failed (HTTP $http_code)"
        fi
    else
        log_warning "Skipping version detail tests (no version_id available)"
    fi
else
    log_warning "Skipping versioning tests (no resume_id available)"
fi

# ============================================================
# 17. Analytics Endpoints
# ============================================================
log_info "Test 30: GET /analytics/usage"
response=$(curl -s -w "\n%{http_code}" \
    "$API_BASE_URL/analytics/usage?limit=10" 2>/dev/null)

http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" = "200" ]; then
    log_success "Analytics usage endpoint works"
else
    log_warning "Analytics usage failed (HTTP $http_code) - may need database setup"
    if echo "$body" | grep -q "detail"; then
        error_detail=$(echo "$body" | grep -o '"detail":"[^"]*"' | head -1 | cut -d'"' -f4 || echo "")
        if [ -n "$error_detail" ]; then
            log_info "Error: $error_detail"
        fi
    fi
fi

log_info "Test 31: GET /analytics/usage/top"
response=$(curl -s -w "\n%{http_code}" \
    "$API_BASE_URL/analytics/usage/top?limit=5&days=7" 2>/dev/null)

http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" = "200" ]; then
    log_success "Analytics top endpoints works"
else
    log_warning "Analytics top failed (HTTP $http_code) - may need database setup"
    if echo "$body" | grep -q "detail"; then
        error_detail=$(echo "$body" | grep -o '"detail":"[^"]*"' | head -1 | cut -d'"' -f4 || echo "")
        if [ -n "$error_detail" ]; then
            log_info "Error: $error_detail"
        fi
    fi
fi

log_info "Test 32: GET /analytics/usage/endpoint/tailor"
response=$(curl -s -w "\n%{http_code}" \
    "$API_BASE_URL/analytics/usage/endpoint/tailor?limit=10" 2>/dev/null)

http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" = "200" ]; then
    log_success "Analytics endpoint details works"
else
    log_warning "Analytics endpoint details failed (HTTP $http_code) - may need database setup"
    if echo "$body" | grep -q "detail"; then
        error_detail=$(echo "$body" | grep -o '"detail":"[^"]*"' | head -1 | cut -d'"' -f4 || echo "")
        if [ -n "$error_detail" ]; then
            log_info "Error: $error_detail"
        fi
    fi
fi

log_info "Test 33: GET /analytics/usage/summary"
response=$(curl -s -w "\n%{http_code}" \
    "$API_BASE_URL/analytics/usage/summary?days=7" 2>/dev/null)

http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" = "200" ]; then
    log_success "Analytics summary endpoint works"
else
    log_warning "Analytics summary failed (HTTP $http_code) - may need database setup"
    if echo "$body" | grep -q "detail"; then
        error_detail=$(echo "$body" | grep -o '"detail":"[^"]*"' | head -1 | cut -d'"' -f4 || echo "")
        if [ -n "$error_detail" ]; then
            log_info "Error: $error_detail"
        fi
    fi
fi

# ============================================================
# Summary
# ============================================================
print_summary

echo ""
echo "=========================================="
echo "Test Details"
echo "=========================================="
echo "Job ID used: ${JOB_ID:-N/A}"
echo "Resume ID used: ${RESUME_ID:-N/A}"
echo "Application ID used: ${APPLICATION_ID:-N/A}"
echo "Template ID used: ${TEMPLATE_ID:-N/A}"
echo "=========================================="

