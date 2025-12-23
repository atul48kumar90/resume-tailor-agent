#!/bin/bash
# check_services.sh - Verify local dependencies are running and env vars are set.
#
# Checks:
#  - PostgreSQL on port 5432
#  - Redis on port 6379
#  - RQ worker process
#  - Required env vars: OPENAI_API_KEY, DATABASE_URL, REDIS_URL
#
# Note: This script only checks status; it does not start services automatically.
# For macOS with Homebrew, suggested start commands are printed if services are down.

set -euo pipefail

yellow() { printf "\033[33m%s\033[0m\n" "$*"; }
green() { printf "\033[32m%s\033[0m\n" "$*"; }
red() { printf "\033[31m%s\033[0m\n" "$*"; }

check_port() {
  local host="$1" port="$2" name="$3"
  if nc -z "$host" "$port" 2>/dev/null; then
    green "✅ $name is listening on $host:$port"
    return 0
  else
    red "❌ $name is NOT reachable on $host:$port"
    return 1
  fi
}

check_env() {
  local var="$1"
  if [ -n "${!var-}" ]; then
    green "✅ $var is set"
  else
    red "❌ $var is NOT set"
  fi
}

echo "=========================================="
echo "Service & Environment Checks"
echo "=========================================="

# Env vars
check_env "OPENAI_API_KEY"
check_env "DATABASE_URL"
check_env "REDIS_URL"
echo ""

# PostgreSQL
if check_port "127.0.0.1" 5432 "PostgreSQL"; then
  :
else
  yellow "Suggested start (macOS Homebrew): brew services start postgresql@14"
  yellow "Suggested start (Docker): docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=pass postgres:14"
fi
echo ""

# Redis
if check_port "127.0.0.1" 6379 "Redis"; then
  :
else
  yellow "Suggested start (macOS Homebrew): brew services start redis"
  yellow "Suggested start (Docker): docker run -d -p 6379:6379 redis:7-alpine"
fi
echo ""

# RQ worker
if pgrep -f "rq worker" >/dev/null 2>&1; then
  green "✅ RQ worker process is running"
else
  yellow "⚠️  RQ worker not detected. Start with: rq worker default"
fi

echo ""
echo "Checks complete."

