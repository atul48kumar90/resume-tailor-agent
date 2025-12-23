#!/bin/bash
# test_skill_gap.sh - Test skill gap analysis feature

source "$(dirname "$0")/test_config.sh"

echo "=========================================="
echo "Testing Skill Gap Analysis Feature"
echo "=========================================="

# Create test files if they don't exist
if [ ! -f "$TEST_DATA_DIR/sample_resume.txt" ]; then
    create_test_files
fi

# Test 1: Compare ATS endpoint (includes skill gap analysis)
log_info "Test 1: Testing /ats/compare endpoint with skill gap analysis"
response=$(curl -s -w "\n%{http_code}" \
    -X POST "$API_BASE_URL/ats/compare" \
    -F "jd_file=@$TEST_DATA_DIR/sample_jd.txt" \
    -F "resume=@$TEST_DATA_DIR/sample_resume.txt" 2>/dev/null)

http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" = "200" ]; then
    # Check if skill_gap_analysis is in response
    if echo "$body" | grep -q "skill_gap_analysis"; then
        log_success "Skill gap analysis included in response"
        
        # Validate skill gap structure
        if echo "$body" | grep -q '"summary"'; then
            log_success "Skill gap has summary section"
        else
            log_error "Skill gap missing summary section"
        fi
        
        if echo "$body" | grep -q '"missing_skills"'; then
            log_success "Skill gap has missing_skills section"
        else
            log_error "Skill gap missing missing_skills section"
        fi
        
        if echo "$body" | grep -q '"recommendations"'; then
            log_success "Skill gap has recommendations section"
        else
            log_error "Skill gap missing recommendations section"
        fi
        
        if echo "$body" | grep -q '"gap_severity"'; then
            log_success "Skill gap has gap_severity"
        else
            log_error "Skill gap missing gap_severity"
        fi
        
        # Save response for inspection
        echo "$body" | jq '.' > "$TEST_DATA_DIR/skill_gap_response.json" 2>/dev/null || echo "$body" > "$TEST_DATA_DIR/skill_gap_response.json"
        log_info "Response saved to $TEST_DATA_DIR/skill_gap_response.json"
        
        # Extract and display key metrics
        if command -v jq &> /dev/null; then
            required_coverage=$(jq -r '.skill_gap_analysis.summary.required_coverage' "$TEST_DATA_DIR/skill_gap_response.json" 2>/dev/null)
            gap_severity=$(jq -r '.skill_gap_analysis.gap_severity' "$TEST_DATA_DIR/skill_gap_response.json" 2>/dev/null)
            log_info "Required Skills Coverage: ${required_coverage}%"
            log_info "Gap Severity: $gap_severity"
        fi
    else
        log_error "Skill gap analysis not found in response"
    fi
else
    log_error "Failed to get comparison (HTTP $http_code)"
    echo "$body"
fi

# Test 2: Validate skill gap data quality
log_info "Test 2: Validating skill gap data quality"
if [ -f "$TEST_DATA_DIR/skill_gap_response.json" ] && command -v jq &> /dev/null; then
    missing_required_count=$(jq -r '.skill_gap_analysis.missing_skills.required_skills | length' "$TEST_DATA_DIR/skill_gap_response.json" 2>/dev/null)
    present_required_count=$(jq -r '.skill_gap_analysis.present_skills.required_skills | length' "$TEST_DATA_DIR/skill_gap_response.json" 2>/dev/null)
    
    if [ "$missing_required_count" != "null" ] && [ "$present_required_count" != "null" ]; then
        log_success "Skill gap data is valid (Missing: $missing_required_count, Present: $present_required_count)"
    else
        log_error "Skill gap data is invalid"
    fi
fi

print_summary

