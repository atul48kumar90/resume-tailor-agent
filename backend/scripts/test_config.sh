#!/bin/bash
# test_config.sh - Configuration for test scripts

# API Configuration
API_BASE_URL="${API_BASE_URL:-http://localhost:8000}"
API_HEALTH_URL="${API_BASE_URL}/health"

# Test Data Directory
TEST_DATA_DIR="${TEST_DATA_DIR:-./test_data}"
mkdir -p "$TEST_DATA_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test result tracking
PASSED=0
FAILED=0
TOTAL=0

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[PASS]${NC} $1"
    ((PASSED++))
    ((TOTAL++))
}

log_error() {
    echo -e "${RED}[FAIL]${NC} $1"
    ((FAILED++))
    ((TOTAL++))
}

log_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# Check if API is running
check_api_health() {
    log_info "Checking API health at $API_HEALTH_URL"
    response=$(curl -s -w "\n%{http_code}" "$API_HEALTH_URL" 2>/dev/null)
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" = "200" ] || [ "$http_code" = "503" ]; then
        log_success "API is reachable (HTTP $http_code)"
        return 0
    else
        log_error "API is not reachable (HTTP $http_code)"
        return 1
    fi
}

# Create sample test files
create_test_files() {
    log_info "Creating sample test files..."
    
    # Sample resume text
    cat > "$TEST_DATA_DIR/sample_resume.txt" << 'EOF'
John Doe
Software Engineer
Email: john.doe@email.com | Phone: (555) 123-4567

SUMMARY
Experienced software engineer with 5+ years developing scalable backend systems using Java, Spring Boot, and microservices architecture. Strong expertise in REST APIs, database design, and cloud technologies.

EXPERIENCE

Senior Software Engineer | Tech Corp | 2020 - Present
- Developed and maintained microservices using Spring Boot and Java
- Designed REST APIs serving 1M+ requests per day
- Implemented database solutions using PostgreSQL and Redis
- Worked with Docker and Kubernetes for containerization
- Collaborated with cross-functional teams using Agile methodologies

Software Engineer | Startup Inc | 2018 - 2020
- Built backend services using Java and Spring Framework
- Created RESTful APIs for mobile and web applications
- Optimized database queries improving performance by 40%
- Participated in code reviews and technical design discussions

SKILLS
Java, Spring Boot, REST APIs, PostgreSQL, Redis, Docker, Kubernetes, Microservices, Git, Agile
EOF

    # Sample job description
    cat > "$TEST_DATA_DIR/sample_jd.txt" << 'EOF'
Software Engineer - Backend

We are looking for an experienced Software Engineer to join our backend team.

Required Skills:
- Java programming (5+ years)
- Spring Boot framework
- REST API design and development
- Microservices architecture
- PostgreSQL database
- Docker and containerization

Preferred Skills:
- Kubernetes experience
- Redis caching
- Cloud platforms (AWS, GCP, or Azure)
- CI/CD pipelines

Responsibilities:
- Design and develop scalable backend services
- Build RESTful APIs
- Optimize database performance
- Work with microservices architecture
- Collaborate with frontend and DevOps teams
EOF

    # Second JD for batch testing
    cat > "$TEST_DATA_DIR/sample_jd2.txt" << 'EOF'
Senior Backend Engineer

Join our team as a Senior Backend Engineer working on high-scale systems.

Required:
- Java (7+ years)
- Spring Boot and Spring Framework
- Microservices
- REST APIs
- SQL databases
- Docker

Nice to have:
- Kubernetes
- Redis
- Message queues (Kafka, RabbitMQ)
- AWS services
EOF

    # Third JD for batch testing
    cat > "$TEST_DATA_DIR/sample_jd3.txt" << 'EOF'
Full Stack Developer

We need a Full Stack Developer with strong backend skills.

Requirements:
- Java or Python
- REST API development
- Database design
- Frontend experience (React, Angular, or Vue)
- Git version control
EOF

    log_success "Test files created in $TEST_DATA_DIR"
}

# Print test summary
print_summary() {
    echo ""
    echo "=========================================="
    echo "Test Summary"
    echo "=========================================="
    echo -e "Total Tests: $TOTAL"
    echo -e "${GREEN}Passed: $PASSED${NC}"
    echo -e "${RED}Failed: $FAILED${NC}"
    echo "=========================================="
    
    if [ $FAILED -eq 0 ]; then
        echo -e "${GREEN}All tests passed!${NC}"
        return 0
    else
        echo -e "${RED}Some tests failed!${NC}"
        return 1
    fi
}

