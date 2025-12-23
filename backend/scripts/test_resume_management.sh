#!/bin/bash
# test_resume_management.sh - Test resume management dashboard feature

source "$(dirname "$0")/test_config.sh"

echo "=========================================="
echo "Testing Resume Management Feature"
echo "=========================================="

# Create test files if they don't exist
if [ ! -f "$TEST_DATA_DIR/sample_resume.txt" ]; then
    create_test_files
fi

RESUME_ID=""
APPLICATION_ID=""

# Test 1: Create resume entry
log_info "Test 1: Creating resume entry"
response=$(curl -s -w "\n%{http_code}" \
    -X POST "$API_BASE_URL/resumes" \
    -F "title=Test Resume - Software Engineer" \
    -F "tags=backend,java,spring" \
    -F "user_id=test_user" 2>/dev/null)

http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" = "200" ]; then
    log_success "Resume entry created successfully"
    
    # Extract resume_id
    if command -v jq &> /dev/null; then
        RESUME_ID=$(echo "$body" | jq -r '.resume_id' 2>/dev/null)
    else
        # Fallback: try to extract from response
        RESUME_ID=$(echo "$body" | grep -o '"resume_id":"[^"]*' | cut -d'"' -f4)
    fi
    
    if [ -n "$RESUME_ID" ] && [ "$RESUME_ID" != "null" ]; then
        log_success "Resume ID extracted: $RESUME_ID"
        echo "$body" | jq '.' > "$TEST_DATA_DIR/resume_create_response.json" 2>/dev/null || echo "$body" > "$TEST_DATA_DIR/resume_create_response.json"
    else
        log_error "Failed to extract resume ID"
        RESUME_ID=""
    fi
else
    log_error "Failed to create resume entry (HTTP $http_code)"
    echo "$body"
fi

# Test 2: List resumes
log_info "Test 2: Listing resumes"
response=$(curl -s -w "\n%{http_code}" \
    -X GET "$API_BASE_URL/resumes?user_id=test_user" 2>/dev/null)

http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" = "200" ]; then
    log_success "List resumes request successful"
    
    if echo "$body" | grep -q '"resumes"'; then
        log_success "Response contains resumes list"
        
        if command -v jq &> /dev/null; then
            count=$(echo "$body" | jq -r '.count' 2>/dev/null)
            log_info "Resume count: $count"
        fi
    else
        log_error "Response missing resumes list"
    fi
else
    log_error "Failed to list resumes (HTTP $http_code)"
fi

# Test 3: Get resume details
if [ -n "$RESUME_ID" ]; then
    log_info "Test 3: Getting resume details for $RESUME_ID"
    response=$(curl -s -w "\n%{http_code}" \
        -X GET "$API_BASE_URL/resumes/$RESUME_ID" 2>/dev/null)
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" = "200" ]; then
        log_success "Get resume details successful"
        
        if echo "$body" | grep -q '"resume_id"'; then
            log_success "Response contains resume data"
        else
            log_error "Response missing resume data"
        fi
    else
        log_error "Failed to get resume details (HTTP $http_code)"
    fi
else
    log_warning "Skipping get resume details test (no resume ID)"
fi

# Test 4: Create application
if [ -n "$RESUME_ID" ]; then
    log_info "Test 4: Creating application for resume $RESUME_ID"
    response=$(curl -s -w "\n%{http_code}" \
        -X POST "$API_BASE_URL/resumes/$RESUME_ID/applications" \
        -F "jd_file=@$TEST_DATA_DIR/sample_jd.txt" \
        -F "jd_title=Software Engineer" \
        -F "company=Tech Corp" \
        -F "status=applied" \
        -F "ats_score=75" \
        -F "notes=Initial application submitted" 2>/dev/null)
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" = "200" ]; then
        log_success "Application created successfully"
        
        # Extract application_id
        if command -v jq &> /dev/null; then
            APPLICATION_ID=$(echo "$body" | jq -r '.application_id' 2>/dev/null)
        else
            APPLICATION_ID=$(echo "$body" | grep -o '"application_id":"[^"]*' | cut -d'"' -f4)
        fi
        
        if [ -n "$APPLICATION_ID" ] && [ "$APPLICATION_ID" != "null" ]; then
            log_success "Application ID extracted: $APPLICATION_ID"
        else
            log_error "Failed to extract application ID"
            APPLICATION_ID=""
        fi
    else
        log_error "Failed to create application (HTTP $http_code)"
        echo "$body"
    fi
else
    log_warning "Skipping create application test (no resume ID)"
fi

# Test 5: Update application status
if [ -n "$APPLICATION_ID" ]; then
    log_info "Test 5: Updating application status to 'interview'"
    response=$(curl -s -w "\n%{http_code}" \
        -X PATCH "$API_BASE_URL/applications/$APPLICATION_ID" \
        -F "status=interview" \
        -F "notes=Received interview invitation" 2>/dev/null)
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" = "200" ]; then
        log_success "Application status updated successfully"
    else
        log_error "Failed to update application status (HTTP $http_code)"
        echo "$body"
    fi
else
    log_warning "Skipping update application test (no application ID)"
fi

# Test 6: Get dashboard
log_info "Test 6: Getting dashboard statistics"
response=$(curl -s -w "\n%{http_code}" \
    -X GET "$API_BASE_URL/dashboard?user_id=test_user" 2>/dev/null)

http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" = "200" ]; then
    log_success "Dashboard request successful"
    
    if echo "$body" | grep -q '"total_resumes"'; then
        log_success "Dashboard contains statistics"
        
        if command -v jq &> /dev/null; then
            total_resumes=$(echo "$body" | jq -r '.total_resumes' 2>/dev/null)
            total_applications=$(echo "$body" | jq -r '.total_applications' 2>/dev/null)
            log_info "Total Resumes: $total_resumes"
            log_info "Total Applications: $total_applications"
        fi
    else
        log_error "Dashboard missing statistics"
    fi
else
    log_error "Failed to get dashboard (HTTP $http_code)"
fi

print_summary

