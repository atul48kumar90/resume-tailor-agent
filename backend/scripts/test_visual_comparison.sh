#!/bin/bash
# test_visual_comparison.sh - Test visual before/after comparison feature

source "$(dirname "$0")/test_config.sh"

echo "=========================================="
echo "Testing Visual Comparison Feature"
echo "=========================================="

# Create test files if they don't exist
if [ ! -f "$TEST_DATA_DIR/sample_resume.txt" ]; then
    create_test_files
fi

# Test 1: Compare ATS endpoint (includes visual comparison)
log_info "Test 1: Testing /ats/compare endpoint with visual comparison"
response=$(curl -s -w "\n%{http_code}" \
    -X POST "$API_BASE_URL/ats/compare" \
    -F "jd_file=@$TEST_DATA_DIR/sample_jd.txt" \
    -F "resume=@$TEST_DATA_DIR/sample_resume.txt" 2>/dev/null)

http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" = "200" ]; then
    # Check if visual_comparison is in response
    if echo "$body" | grep -q "visual_comparison"; then
        log_success "Visual comparison included in response"
        
        # Extract and validate visual comparison structure
        if echo "$body" | grep -q '"summary"'; then
            log_success "Visual comparison has summary section"
        else
            log_error "Visual comparison missing summary section"
        fi
        
        if echo "$body" | grep -q '"experience"'; then
            log_success "Visual comparison has experience section"
        else
            log_error "Visual comparison missing experience section"
        fi
        
        if echo "$body" | grep -q '"skills"'; then
            log_success "Visual comparison has skills section"
        else
            log_error "Visual comparison missing skills section"
        fi
        
        if echo "$body" | grep -q '"text_diff"'; then
            log_success "Visual comparison has text diff"
        else
            log_error "Visual comparison missing text diff"
        fi
        
        # Save response for inspection
        echo "$body" | jq '.' > "$TEST_DATA_DIR/visual_comparison_response.json" 2>/dev/null || echo "$body" > "$TEST_DATA_DIR/visual_comparison_response.json"
        log_info "Response saved to $TEST_DATA_DIR/visual_comparison_response.json"
    else
        log_error "Visual comparison not found in response"
    fi
else
    log_error "Failed to get comparison (HTTP $http_code)"
    echo "$body"
fi

# Test 2: Validate visual comparison structure
log_info "Test 2: Validating visual comparison structure"
if [ -f "$TEST_DATA_DIR/visual_comparison_response.json" ]; then
    # Check if jq is available for JSON parsing
    if command -v jq &> /dev/null; then
        summary_changed=$(jq -r '.visual_comparison.summary.changed' "$TEST_DATA_DIR/visual_comparison_response.json" 2>/dev/null)
        if [ "$summary_changed" != "null" ]; then
            log_success "Visual comparison structure is valid"
        else
            log_error "Visual comparison structure is invalid"
        fi
    else
        log_warning "jq not installed, skipping JSON validation"
    fi
fi

print_summary

