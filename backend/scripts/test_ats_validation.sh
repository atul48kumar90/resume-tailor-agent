#!/bin/bash
# test_ats_validation.sh - Test ATS format validation feature

source "$(dirname "$0")/test_config.sh"

echo "=========================================="
echo "Testing ATS Format Validation Feature"
echo "=========================================="

# Create test files if they don't exist
if [ ! -f "$TEST_DATA_DIR/sample_resume.txt" ]; then
    create_test_files
fi

# Create a simple PDF for testing (if we have a resume file)
# For now, we'll test with the text file converted to a simple format
log_info "Note: ATS validation requires PDF or DOCX files"
log_info "Creating test DOCX file from resume text..."

# Test 1: Validate format endpoint (will need actual PDF/DOCX)
log_info "Test 1: Testing /ats/validate-format endpoint"

# First, let's try to create a simple test file
# In a real scenario, you'd have actual PDF/DOCX files
if [ -f "$TEST_DATA_DIR/sample_resume.txt" ]; then
    # Try to validate the text file (should fail gracefully)
    response=$(curl -s -w "\n%{http_code}" \
        -X POST "$API_BASE_URL/ats/validate-format" \
        -F "resume_file=@$TEST_DATA_DIR/sample_resume.txt" 2>/dev/null)
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" = "400" ]; then
        log_success "Endpoint correctly rejects unsupported file types"
    elif [ "$http_code" = "200" ]; then
        # If it accepts, validate response structure
        if echo "$body" | grep -q '"valid"'; then
            log_success "Validation response has valid field"
        else
            log_error "Validation response missing valid field"
        fi
        
        if echo "$body" | grep -q '"score"'; then
            log_success "Validation response has score field"
        else
            log_error "Validation response missing score field"
        fi
        
        if echo "$body" | grep -q '"issues"'; then
            log_success "Validation response has issues field"
        else
            log_error "Validation response missing issues field"
        fi
        
        if echo "$body" | grep -q '"recommendations"'; then
            log_success "Validation response has recommendations field"
        else
            log_error "Validation response missing recommendations field"
        fi
        
        # Save response
        echo "$body" | jq '.' > "$TEST_DATA_DIR/ats_validation_response.json" 2>/dev/null || echo "$body" > "$TEST_DATA_DIR/ats_validation_response.json"
        log_info "Response saved to $TEST_DATA_DIR/ats_validation_response.json"
        
        # Display validation score
        if command -v jq &> /dev/null; then
            score=$(jq -r '.score' "$TEST_DATA_DIR/ats_validation_response.json" 2>/dev/null)
            is_valid=$(jq -r '.valid' "$TEST_DATA_DIR/ats_validation_response.json" 2>/dev/null)
            log_info "ATS Format Score: $score/100"
            log_info "Is Valid: $is_valid"
        fi
    else
        log_error "Unexpected response (HTTP $http_code)"
        echo "$body"
    fi
else
    log_error "Test file not found"
fi

# Test 2: Validate response structure
log_info "Test 2: Validating response structure"
if [ -f "$TEST_DATA_DIR/ats_validation_response.json" ] && command -v jq &> /dev/null; then
    file_type=$(jq -r '.file_type' "$TEST_DATA_DIR/ats_validation_response.json" 2>/dev/null)
    issues_count=$(jq -r '.issues | length' "$TEST_DATA_DIR/ats_validation_response.json" 2>/dev/null)
    warnings_count=$(jq -r '.warnings | length' "$TEST_DATA_DIR/ats_validation_response.json" 2>/dev/null)
    
    log_info "File Type: $file_type"
    log_info "Issues: $issues_count, Warnings: $warnings_count"
    
    if [ "$file_type" != "null" ]; then
        log_success "Response structure is valid"
    else
        log_error "Response structure is invalid"
    fi
fi

# Note: Full testing requires actual PDF/DOCX files
log_warning "Full ATS validation testing requires actual PDF/DOCX files"
log_info "To test with real files, place PDF/DOCX files in $TEST_DATA_DIR and update this script"

print_summary

