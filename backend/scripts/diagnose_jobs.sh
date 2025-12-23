#!/bin/bash
# diagnose_jobs.sh - Diagnose why jobs are stuck in pending status

echo "=========================================="
echo "Job Queue Diagnostics"
echo "=========================================="

# Get the project root directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

# Check if virtual environment exists and activate it
if [ -d ".venv" ]; then
    source .venv/bin/activate
elif [ -d "venv" ]; then
    source venv/bin/activate
fi

echo ""
echo "1. Checking RQ Queue Status..."
python3 << 'PYTHON_SCRIPT'
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent if '__file__' in dir() else Path.cwd()
sys.path.insert(0, str(project_root))

from core.job_queue import get_queue, get_rq_redis_client
from rq import Queue
from rq.job import Job
import redis

try:
    rq_client = get_rq_redis_client()
    if not rq_client:
        print("❌ RQ Redis client not available")
        sys.exit(1)
    
    queue = get_queue("default")
    if not queue:
        print("❌ Queue not available")
        sys.exit(1)
    
    print(f"✅ Queue 'default' found")
    print(f"   Jobs in queue: {len(queue)}")
    print(f"   Started jobs: {len(queue.started_job_registry)}")
    print(f"   Finished jobs: {len(queue.finished_job_registry)}")
    print(f"   Failed jobs: {len(queue.failed_job_registry)}")
    
    # Get recent jobs
    print("\n2. Recent Jobs in Queue:")
    job_ids = queue.job_ids[:10]  # First 10 jobs
    if job_ids:
        for jid in job_ids:
            try:
                job = Job.fetch(jid, connection=rq_client)
                print(f"   Job {jid}:")
                print(f"      Status: {job.get_status()}")
                print(f"      Created: {job.created_at}")
                if job.started_at:
                    print(f"      Started: {job.started_at}")
                if job.ended_at:
                    print(f"      Ended: {job.ended_at}")
                if job.is_failed:
                    print(f"      Error: {str(job.exc_info)[:200] if job.exc_info else 'Unknown'}")
            except Exception as e:
                print(f"   Job {jid}: Error fetching - {e}")
    else:
        print("   No jobs in queue")
    
    # Check started jobs
    print("\n3. Started Jobs (currently processing):")
    started_ids = list(queue.started_job_registry.get_job_ids()[:10])
    if started_ids:
        for jid in started_ids:
            try:
                job = Job.fetch(jid, connection=rq_client)
                print(f"   Job {jid}: Started at {job.started_at}")
            except Exception as e:
                print(f"   Job {jid}: Error - {e}")
    else:
        print("   No jobs currently processing")
    
    # Check failed jobs
    print("\n4. Recent Failed Jobs:")
    failed_ids = list(queue.failed_job_registry.get_job_ids()[:5])
    if failed_ids:
        for jid in failed_ids:
            try:
                job = Job.fetch(jid, connection=rq_client)
                print(f"   Job {jid}:")
                print(f"      Failed at: {job.ended_at}")
                print(f"      Error: {str(job.exc_info)[:300] if job.exc_info else 'Unknown'}")
            except Exception as e:
                print(f"   Job {jid}: Error - {e}")
    else:
        print("   No failed jobs")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
PYTHON_SCRIPT

echo ""
echo "5. Checking Worker Status..."
if pgrep -f "workers.job_worker" > /dev/null 2>&1; then
    echo "✅ Worker process is running"
    echo "   PID: $(pgrep -f 'workers.job_worker')"
else
    echo "❌ Worker process is NOT running"
    echo "   Start with: cd backend && ./scripts/start_worker.sh"
fi

echo ""
echo "6. Checking Redis Connection..."
if command -v redis-cli &> /dev/null; then
    if redis-cli ping > /dev/null 2>&1; then
        echo "✅ Redis is running"
        echo "   Queue length: $(redis-cli LLEN rq:queue:default 2>/dev/null || echo 'N/A')"
    else
        echo "❌ Redis is not running"
    fi
fi

echo ""
echo "=========================================="
echo "Diagnostics complete"
echo "=========================================="

