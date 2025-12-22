#!/bin/bash
# quick_test.sh - Quick smoke test for basic functionality

source "$(dirname "$0")/test_config.sh"

echo "=========================================="
echo "Quick Smoke Test"
echo "=========================================="

# Check API health
if ! check_api_health; then
    log_error "API is not running. Please start it first."
    exit 1
fi

# Create test files
create_test_files

# Quick test: Health check
log_info "Testing health endpoint..."
response=$(curl -s "$API_BASE_URL/health")
if echo "$response" | grep -q "status"; then
    log_success "Health check passed"
else
    log_error "Health check failed"
    exit 1
fi

# Quick test: ATS compare
log_info "Testing ATS compare endpoint..."
response=$(curl -s -w "\n%{http_code}" \
    -X POST "$API_BASE_URL/ats/compare" \
    -F "jd_file=@$TEST_DATA_DIR/sample_jd.txt" \
    -F "resume=@$TEST_DATA_DIR/sample_resume.txt" 2>/dev/null)

http_code=$(echo "$response" | tail -n1)
if [ "$http_code" = "200" ]; then
    log_success "ATS compare endpoint working"
    
    # Check for key fields
    body=$(echo "$response" | sed '$d')
    if echo "$body" | grep -q "before" && echo "$body" | grep -q "after"; then
        log_success "Response contains before/after scores"
    fi
    
    if echo "$body" | grep -q "visual_comparison"; then
        log_success "Visual comparison included"
    fi
    
    if echo "$body" | grep -q "skill_gap_analysis"; then
        log_success "Skill gap analysis included"
    fi
else
    log_error "ATS compare failed (HTTP $http_code)"
    exit 1
fi

echo ""
log_success "Quick smoke test passed! ✅"
echo "Run ./test_e2e.sh for comprehensive testing"

