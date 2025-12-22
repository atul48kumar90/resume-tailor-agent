#!/bin/bash
# test_e2e.sh - End-to-end test script for all features

source "$(dirname "$0")/test_config.sh"

echo "=========================================="
echo "End-to-End Test Suite"
echo "=========================================="
echo ""

# Check if API is running
if ! check_api_health; then
    log_error "API is not running. Please start the API server first."
    log_info "To start the API: uvicorn api.main:app --reload"
    exit 1
fi

echo ""
echo "Creating test files..."
create_test_files
echo ""

# Track overall results
OVERALL_PASSED=0
OVERALL_FAILED=0

# Run individual test scripts
echo "=========================================="
echo "1. Testing Visual Comparison"
echo "=========================================="
if bash "$(dirname "$0")/test_visual_comparison.sh"; then
    ((OVERALL_PASSED++))
else
    ((OVERALL_FAILED++))
fi
echo ""

echo "=========================================="
echo "2. Testing Skill Gap Analysis"
echo "=========================================="
if bash "$(dirname "$0")/test_skill_gap.sh"; then
    ((OVERALL_PASSED++))
else
    ((OVERALL_FAILED++))
fi
echo ""

echo "=========================================="
echo "3. Testing Batch Processing"
echo "=========================================="
if bash "$(dirname "$0")/test_batch_processing.sh"; then
    ((OVERALL_PASSED++))
else
    ((OVERALL_FAILED++))
fi
echo ""

echo "=========================================="
echo "4. Testing ATS Format Validation"
echo "=========================================="
if bash "$(dirname "$0")/test_ats_validation.sh"; then
    ((OVERALL_PASSED++))
else
    ((OVERALL_FAILED++))
fi
echo ""

echo "=========================================="
echo "5. Testing Resume Management"
echo "=========================================="
if bash "$(dirname "$0")/test_resume_management.sh"; then
    ((OVERALL_PASSED++))
else
    ((OVERALL_FAILED++))
fi
echo ""

# Final summary
echo "=========================================="
echo "End-to-End Test Summary"
echo "=========================================="
echo -e "Test Suites Passed: ${GREEN}$OVERALL_PASSED${NC}"
echo -e "Test Suites Failed: ${RED}$OVERALL_FAILED${NC}"
echo "=========================================="

if [ $OVERALL_FAILED -eq 0 ]; then
    echo -e "${GREEN}All test suites passed!${NC}"
    exit 0
else
    echo -e "${RED}Some test suites failed!${NC}"
    exit 1
fi

