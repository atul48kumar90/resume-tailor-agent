#!/bin/bash

# Script to clear Redis cache for resume tailor agent
# Usage:
#   ./scripts/clear_cache.sh              # Clear all cache
#   ./scripts/clear_cache.sh rewrite      # Clear only rewrite cache
#   ./scripts/clear_cache.sh jd           # Clear only JD analysis cache
#   ./scripts/clear_cache.sh ats          # Clear only ATS score cache
#   ./scripts/clear_cache.sh all          # Clear all cache (same as no argument)

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Redis is running
if ! redis-cli ping > /dev/null 2>&1; then
    echo -e "${RED}Error: Redis is not running or not accessible${NC}"
    echo "Please start Redis first:"
    echo "  - macOS: brew services start redis"
    echo "  - Docker: docker run -d -p 6379:6379 redis:7"
    exit 1
fi

# Get cache type from argument (default: all)
CACHE_TYPE=${1:-all}

echo -e "${YELLOW}Clearing Redis cache...${NC}"

case $CACHE_TYPE in
    rewrite)
        echo "Clearing resume rewrite cache..."
        COUNT=$(redis-cli --scan --pattern "rewrite:*" | wc -l | tr -d ' ')
        redis-cli --scan --pattern "rewrite:*" | xargs -r redis-cli del
        echo -e "${GREEN}✓ Cleared $COUNT rewrite cache entries${NC}"
        ;;
    jd)
        echo "Clearing JD analysis cache..."
        COUNT=$(redis-cli --scan --pattern "jd:*" | wc -l | tr -d ' ')
        redis-cli --scan --pattern "jd:*" | xargs -r redis-cli del
        echo -e "${GREEN}✓ Cleared $COUNT JD analysis cache entries${NC}"
        ;;
    ats)
        echo "Clearing ATS score cache..."
        COUNT=$(redis-cli --scan --pattern "ats:*" | wc -l | tr -d ' ')
        redis-cli --scan --pattern "ats:*" | xargs -r redis-cli del
        echo -e "${GREEN}✓ Cleared $COUNT ATS score cache entries${NC}"
        ;;
    all|*)
        echo "Clearing all cache entries..."
        
        # Count and clear each cache type
        REWRITE_COUNT=$(redis-cli --scan --pattern "rewrite:*" | wc -l | tr -d ' ')
        JD_COUNT=$(redis-cli --scan --pattern "jd:*" | wc -l | tr -d ' ')
        ATS_COUNT=$(redis-cli --scan --pattern "ats:*" | wc -l | tr -d ' ')
        NORMALIZED_COUNT=$(redis-cli --scan --pattern "normalized:*" | wc -l | tr -d ' ')
        EXTRACTED_COUNT=$(redis-cli --scan --pattern "extracted:*" | wc -l | tr -d ' ')
        TOKENS_COUNT=$(redis-cli --scan --pattern "tokens:*" | wc -l | tr -d ' ')
        
        # Clear all cache patterns
        redis-cli --scan --pattern "rewrite:*" | xargs -r redis-cli del
        redis-cli --scan --pattern "jd:*" | xargs -r redis-cli del
        redis-cli --scan --pattern "ats:*" | xargs -r redis-cli del
        redis-cli --scan --pattern "normalized:*" | xargs -r redis-cli del
        redis-cli --scan --pattern "extracted:*" | xargs -r redis-cli del
        redis-cli --scan --pattern "tokens:*" | xargs -r redis-cli del
        
        TOTAL=$((REWRITE_COUNT + JD_COUNT + ATS_COUNT + NORMALIZED_COUNT + EXTRACTED_COUNT + TOKENS_COUNT))
        
        echo -e "${GREEN}✓ Cleared all cache entries:${NC}"
        echo "  - Rewrite cache: $REWRITE_COUNT entries"
        echo "  - JD analysis cache: $JD_COUNT entries"
        echo "  - ATS score cache: $ATS_COUNT entries"
        echo "  - Normalized text cache: $NORMALIZED_COUNT entries"
        echo "  - Extracted text cache: $EXTRACTED_COUNT entries"
        echo "  - Tokens cache: $TOKENS_COUNT entries"
        echo -e "${GREEN}Total: $TOTAL entries cleared${NC}"
        ;;
esac

echo -e "${GREEN}Cache cleared successfully!${NC}"

