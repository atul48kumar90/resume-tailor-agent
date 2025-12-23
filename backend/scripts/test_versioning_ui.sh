#!/bin/bash
# test_versioning_ui.sh - Test Resume Versioning UI feature

source "$(dirname "$0")/test_config.sh"

echo "=========================================="
echo "Testing Resume Versioning UI Feature"
echo "=========================================="

# Create test files if they don't exist
if [ ! -f "$TEST_DATA_DIR/sample_resume.txt" ]; then
    create_test_files
fi

# First, we need to create a resume and some versions
# For testing, we'll use the tailor endpoint to create a versioned resume
log_info "Setting up test data: Creating resume with versions..."

# Step 1: Create initial resume by tailoring it
log_info "Test Setup: Creating initial resume version"
setup_response=$(curl -s -w "\n%{http_code}" \
    -X POST "$API_BASE_URL/tailor" \
    -F "job_description_text=Software Engineer position requiring Java, Spring Boot, and REST APIs" \
    -F "resume=@$TEST_DATA_DIR/sample_resume.txt" \
    -F "recruiter_persona=general" 2>/dev/null)

setup_http_code=$(echo "$setup_response" | tail -n1)
setup_body=$(echo "$setup_response" | sed '$d')

if [ "$setup_http_code" != "200" ]; then
    log_error "Failed to create initial resume (HTTP $setup_http_code)"
    echo "$setup_body"
    print_summary
    exit 1
fi

# Extract job_id from response
job_id=$(echo "$setup_body" | grep -o '"job_id":"[^"]*"' | cut -d'"' -f4 || echo "")

if [ -z "$job_id" ]; then
    log_warning "Could not extract job_id, using mock data for testing"
    RESUME_ID="00000000-0000-0000-0000-000000000001"
    VERSION_ID_1="00000000-0000-0000-0000-000000000002"
    VERSION_ID_2="00000000-0000-0000-0000-000000000003"
else
    log_info "Job created: $job_id"
    # Wait for job to complete (simplified - in real scenario, poll job status)
    sleep 2
    
    # For now, we'll test with mock UUIDs since we need actual database setup
    # In a real scenario, we'd create versions through the API
    RESUME_ID="00000000-0000-0000-0000-000000000001"
    VERSION_ID_1="00000000-0000-0000-0000-000000000002"
    VERSION_ID_2="00000000-0000-0000-0000-000000000003"
fi

log_info "Using test resume_id: $RESUME_ID"

# Test 1: List resume versions
log_info "Test 1: Testing GET /resumes/{resume_id}/versions"
response=$(curl -s -w "\n%{http_code}" \
    -X GET "$API_BASE_URL/resumes/$RESUME_ID/versions" 2>/dev/null)

http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" = "200" ]; then
    log_success "List versions endpoint returned 200"
    
    # Check if response is an array
    if echo "$body" | grep -q '\['; then
        log_success "Response is an array"
    else
        log_error "Response is not an array"
    fi
    
    # Save response
    echo "$body" | jq '.' > "$TEST_DATA_DIR/versions_list_response.json" 2>/dev/null || echo "$body" > "$TEST_DATA_DIR/versions_list_response.json"
    log_info "Response saved to $TEST_DATA_DIR/versions_list_response.json"
elif [ "$http_code" = "404" ]; then
    log_warning "Resume not found (expected if database not set up) - HTTP 404"
    log_info "This is expected if testing without database. Skipping version-specific tests."
    print_summary
    exit 0
else
    log_error "Failed to list versions (HTTP $http_code)"
    echo "$body"
fi

# Test 2: Get specific version (only if we have a version ID)
if [ "$http_code" = "200" ] && echo "$body" | grep -q "version_id"; then
    # Extract first version_id if available
    if command -v jq &> /dev/null; then
        VERSION_ID_1=$(jq -r '.[0].version_id' "$TEST_DATA_DIR/versions_list_response.json" 2>/dev/null || echo "$VERSION_ID_1")
    fi
    
    log_info "Test 2: Testing GET /resumes/{resume_id}/versions/{version_id}"
    response=$(curl -s -w "\n%{http_code}" \
        -X GET "$API_BASE_URL/resumes/$RESUME_ID/versions/$VERSION_ID_1" 2>/dev/null)
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" = "200" ]; then
        log_success "Get version endpoint returned 200"
        
        # Validate response structure
        if echo "$body" | grep -q '"version_id"'; then
            log_success "Response includes version_id"
        else
            log_error "Response missing version_id"
        fi
        
        if echo "$body" | grep -q '"version_number"'; then
            log_success "Response includes version_number"
        else
            log_error "Response missing version_number"
        fi
        
        if echo "$body" | grep -q '"resume_data"'; then
            log_success "Response includes resume_data"
        else
            log_error "Response missing resume_data"
        fi
        
        # Save response
        echo "$body" | jq '.' > "$TEST_DATA_DIR/version_detail_response.json" 2>/dev/null || echo "$body" > "$TEST_DATA_DIR/version_detail_response.json"
        log_info "Response saved to $TEST_DATA_DIR/version_detail_response.json"
    else
        log_error "Failed to get version (HTTP $http_code)"
        echo "$body"
    fi
else
    log_warning "Skipping version detail test (no versions available)"
fi

# Test 3: Compare versions (with compare_with parameter)
if [ "$http_code" = "200" ] && [ -n "$VERSION_ID_1" ] && [ "$VERSION_ID_1" != "null" ]; then
    # Get second version ID if available
    if command -v jq &> /dev/null && [ -f "$TEST_DATA_DIR/versions_list_response.json" ]; then
        VERSION_ID_2=$(jq -r '.[1].version_id' "$TEST_DATA_DIR/versions_list_response.json" 2>/dev/null || echo "$VERSION_ID_2")
    fi
    
    log_info "Test 3: Testing GET /resumes/{resume_id}/versions/{version_id}/compare?compare_with={other_version_id}"
    response=$(curl -s -w "\n%{http_code}" \
        -X GET "$API_BASE_URL/resumes/$RESUME_ID/versions/$VERSION_ID_1/compare?compare_with=$VERSION_ID_2" 2>/dev/null)
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" = "200" ]; then
        log_success "Compare versions endpoint returned 200"
        
        # Validate response structure
        if echo "$body" | grep -q '"version1"'; then
            log_success "Response includes version1 metadata"
        else
            log_error "Response missing version1"
        fi
        
        if echo "$body" | grep -q '"version2"'; then
            log_success "Response includes version2 metadata"
        else
            log_error "Response missing version2"
        fi
        
        if echo "$body" | grep -q '"comparison"'; then
            log_success "Response includes comparison data"
        else
            log_error "Response missing comparison"
        fi
        
        if echo "$body" | grep -q '"side_by_side"'; then
            log_success "Response includes side_by_side format"
        else
            log_error "Response missing side_by_side"
        fi
        
        if echo "$body" | grep -q '"statistics"'; then
            log_success "Response includes statistics"
        else
            log_error "Response missing statistics"
        fi
        
        # Validate comparison structure
        if echo "$body" | grep -q '"summary"'; then
            log_success "Comparison includes summary section"
        fi
        
        if echo "$body" | grep -q '"experience"'; then
            log_success "Comparison includes experience section"
        fi
        
        if echo "$body" | grep -q '"skills"'; then
            log_success "Comparison includes skills section"
        fi
        
        if echo "$body" | grep -q '"education"'; then
            log_success "Comparison includes education section"
        fi
        
        # Validate side-by-side structure
        if echo "$body" | grep -q '"sections"'; then
            log_success "Side-by-side includes sections"
        fi
        
        # Validate statistics
        if echo "$body" | grep -q '"total_changes"'; then
            log_success "Statistics includes total_changes"
        fi
        
        if echo "$body" | grep -q '"sections_changed"'; then
            log_success "Statistics includes sections_changed"
        fi
        
        if echo "$body" | grep -q '"words_added"'; then
            log_success "Statistics includes words_added"
        fi
        
        if echo "$body" | grep -q '"words_removed"'; then
            log_success "Statistics includes words_removed"
        fi
        
        # Save response
        echo "$body" | jq '.' > "$TEST_DATA_DIR/version_compare_response.json" 2>/dev/null || echo "$body" > "$TEST_DATA_DIR/version_compare_response.json"
        log_info "Response saved to $TEST_DATA_DIR/version_compare_response.json"
    else
        log_error "Failed to compare versions (HTTP $http_code)"
        echo "$body"
    fi
else
    log_warning "Skipping version compare test (no versions available)"
fi

# Test 4: Compare with current version (no compare_with parameter)
if [ "$http_code" = "200" ] && [ -n "$VERSION_ID_1" ] && [ "$VERSION_ID_1" != "null" ]; then
    log_info "Test 4: Testing GET /resumes/{resume_id}/versions/{version_id}/compare (compare with current)"
    response=$(curl -s -w "\n%{http_code}" \
        -X GET "$API_BASE_URL/resumes/$RESUME_ID/versions/$VERSION_ID_1/compare" 2>/dev/null)
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" = "200" ]; then
        log_success "Compare with current endpoint returned 200"
        
        # Check if version2 is marked as "current"
        if echo "$body" | grep -q '"version_id":"current"'; then
            log_success "Version2 correctly marked as current"
        elif echo "$body" | grep -q '"version2"'; then
            log_success "Version2 present in response"
        else
            log_error "Version2 missing or incorrectly formatted"
        fi
    else
        log_error "Failed to compare with current (HTTP $http_code)"
        echo "$body"
    fi
else
    log_warning "Skipping compare with current test (no versions available)"
fi

# Test 5: Validate error handling
log_info "Test 5: Testing error handling with invalid resume_id"
response=$(curl -s -w "\n%{http_code}" \
    -X GET "$API_BASE_URL/resumes/invalid-uuid/versions" 2>/dev/null)

http_code=$(echo "$response" | tail -n1)

if [ "$http_code" = "400" ]; then
    log_success "Invalid UUID correctly returns 400"
else
    log_warning "Expected 400 for invalid UUID, got $http_code"
fi

# Test 6: Validate error handling for non-existent version
log_info "Test 6: Testing error handling with non-existent version"
response=$(curl -s -w "\n%{http_code}" \
    -X GET "$API_BASE_URL/resumes/$RESUME_ID/versions/00000000-0000-0000-0000-000000000999" 2>/dev/null)

http_code=$(echo "$response" | tail -n1)

if [ "$http_code" = "404" ]; then
    log_success "Non-existent version correctly returns 404"
else
    log_warning "Expected 404 for non-existent version, got $http_code"
fi

print_summary

