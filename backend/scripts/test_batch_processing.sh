#!/bin/bash
# test_batch_processing.sh - Test batch processing feature

source "$(dirname "$0")/test_config.sh"

echo "=========================================="
echo "Testing Batch Processing Feature"
echo "=========================================="

# Create test files if they don't exist
if [ ! -f "$TEST_DATA_DIR/sample_resume.txt" ]; then
    create_test_files
fi

# Test 1: Batch processing with files
log_info "Test 1: Testing /ats/batch endpoint (file-based)"
response=$(curl -s -w "\n%{http_code}" \
    -X POST "$API_BASE_URL/ats/batch" \
    -F "resume=@$TEST_DATA_DIR/sample_resume.txt" \
    -F "jd_files=@$TEST_DATA_DIR/sample_jd.txt" \
    -F "jd_files=@$TEST_DATA_DIR/sample_jd2.txt" \
    -F "jd_files=@$TEST_DATA_DIR/sample_jd3.txt" 2>/dev/null)

http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" = "200" ]; then
    log_success "Batch processing request successful"
    
    # Validate response structure
    if echo "$body" | grep -q '"summary"'; then
        log_success "Batch response has summary section"
    else
        log_error "Batch response missing summary section"
    fi
    
    if echo "$body" | grep -q '"results"'; then
        log_success "Batch response has results section"
    else
        log_error "Batch response missing results section"
    fi
    
    # Save response
    echo "$body" | jq '.' > "$TEST_DATA_DIR/batch_response.json" 2>/dev/null || echo "$body" > "$TEST_DATA_DIR/batch_response.json"
    log_info "Response saved to $TEST_DATA_DIR/batch_response.json"
    
    # Validate results count
    if command -v jq &> /dev/null; then
        results_count=$(jq -r '.results | length' "$TEST_DATA_DIR/batch_response.json" 2>/dev/null)
        total_jds=$(jq -r '.summary.total_jds' "$TEST_DATA_DIR/batch_response.json" 2>/dev/null)
        
        if [ "$results_count" = "$total_jds" ]; then
            log_success "All JDs processed (Count: $results_count)"
        else
            log_error "Mismatch in processed JDs (Expected: $total_jds, Got: $results_count)"
        fi
        
        # Check for best/worst match
        best_match=$(jq -r '.summary.best_match.jd_id' "$TEST_DATA_DIR/batch_response.json" 2>/dev/null)
        if [ "$best_match" != "null" ] && [ "$best_match" != "" ]; then
            log_success "Best match identified: $best_match"
        else
            log_warning "Best match not identified"
        fi
        
        # Display average score
        avg_score=$(jq -r '.summary.average_score' "$TEST_DATA_DIR/batch_response.json" 2>/dev/null)
        log_info "Average ATS Score: $avg_score"
    fi
else
    log_error "Batch processing failed (HTTP $http_code)"
    echo "$body"
fi

# Test 2: Batch processing with text input
log_info "Test 2: Testing /ats/batch/text endpoint (text-based)"
jd1_text=$(cat "$TEST_DATA_DIR/sample_jd.txt")
jd2_text=$(cat "$TEST_DATA_DIR/sample_jd2.txt")

response=$(curl -s -w "\n%{http_code}" \
    -X POST "$API_BASE_URL/ats/batch/text" \
    -F "resume=@$TEST_DATA_DIR/sample_resume.txt" \
    -F "jd_texts=$jd1_text" \
    -F "jd_texts=$jd2_text" \
    -F "jd_titles=Software Engineer" \
    -F "jd_titles=Senior Backend Engineer" 2>/dev/null)

http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" = "200" ]; then
    log_success "Batch text processing request successful"
    
    if echo "$body" | grep -q '"results"'; then
        log_success "Batch text response has results"
    else
        log_error "Batch text response missing results"
    fi
else
    log_error "Batch text processing failed (HTTP $http_code)"
fi

# Test 3: Validate batch processing limits
log_info "Test 3: Testing batch processing limits (should reject >20 JDs)"
# This test would require creating 21 JD files, skipping for now
log_warning "Limit test skipped (would require 21 JD files)"

print_summary

