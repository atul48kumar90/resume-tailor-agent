#!/bin/bash
# check_db_connection.sh - Check and test database connection

echo "=========================================="
echo "Database Connection Checker"
echo "=========================================="

# Check if DATABASE_URL is set
if [ -z "$DATABASE_URL" ]; then
    echo "❌ DATABASE_URL is not set"
    echo ""
    echo "Please set it first. Examples:"
    echo ""
    echo "For custom user (resume_user):"
    echo "  export DATABASE_URL=\"postgresql+asyncpg://resume_user:resume_password@localhost:5432/resume_db\""
    echo ""
    echo "For default postgres user:"
    echo "  export DATABASE_URL=\"postgresql+asyncpg://postgres:yourpassword@localhost:5432/postgres\""
    exit 1
fi

echo "✅ DATABASE_URL is set"
echo "   $DATABASE_URL"
echo ""

# Extract connection details
# Parse DATABASE_URL to get user, password, host, port, database
# Format: postgresql+asyncpg://user:password@host:port/database

SYNC_URL=$(echo "$DATABASE_URL" | sed 's/postgresql+asyncpg:\/\//postgresql:\/\//')
export DATABASE_URL_SYNC="$SYNC_URL"

echo "✅ DATABASE_URL_SYNC: $DATABASE_URL_SYNC"
echo ""

# Check if psycopg2 is installed
if ! python3 -c "import psycopg2" 2>/dev/null; then
    echo "⚠️  psycopg2-binary is not installed"
    echo "   Installing..."
    pip install psycopg2-binary
fi

# Test connection
echo "=========================================="
echo "Testing database connection..."
echo "=========================================="

python3 << EOF
import psycopg2
import sys
import os
from urllib.parse import urlparse

# Parse DATABASE_URL_SYNC
url = os.getenv("DATABASE_URL_SYNC")
if not url:
    print("❌ DATABASE_URL_SYNC is not set")
    sys.exit(1)

# Parse URL
parsed = urlparse(url)
user = parsed.username
password = parsed.password
host = parsed.hostname or "localhost"
port = parsed.port or 5432
database = parsed.path.lstrip("/") or "postgres"

print(f"Attempting to connect to:")
print(f"  Host: {host}")
print(f"  Port: {port}")
print(f"  Database: {database}")
print(f"  User: {user}")
print("")

try:
    conn = psycopg2.connect(
        host=host,
        port=port,
        database=database,
        user=user,
        password=password
    )
    print("✅ Connection successful!")
    
    # Test query
    cur = conn.cursor()
    cur.execute("SELECT version();")
    version = cur.fetchone()[0]
    print(f"✅ PostgreSQL version: {version.split(',')[0]}")
    
    # Check if database exists and list tables
    cur.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
        ORDER BY table_name;
    """)
    tables = cur.fetchall()
    
    if tables:
        print(f"✅ Found {len(tables)} table(s) in database:")
        for table in tables:
            print(f"   - {table[0]}")
    else:
        print("⚠️  No tables found in database (migrations not run yet)")
    
    cur.close()
    conn.close()
    sys.exit(0)
    
except psycopg2.OperationalError as e:
    error_msg = str(e)
    if "password authentication failed" in error_msg:
        print("❌ Password authentication failed")
        print("")
        print("Possible solutions:")
        print("1. Check if your Docker container uses different credentials")
        print("2. Recreate Docker container with matching credentials:")
        print("")
        print("   docker stop <container_name>")
        print("   docker rm <container_name>")
        print("   docker run -d \\")
        print("     --name postgres-resume-tailor \\")
        print("     -p 5432:5432 \\")
        print("     -e POSTGRES_USER=$user \\")
        print("     -e POSTGRES_PASSWORD=$password \\")
        print("     -e POSTGRES_DB=$database \\")
        print("     postgres:14")
        print("")
        print("3. Or update DATABASE_URL to match your existing container")
    elif "could not connect" in error_msg or "Connection refused" in error_msg:
        print("❌ Could not connect to database")
        print("")
        print("Possible solutions:")
        print("1. Check if PostgreSQL is running:")
        print("   docker ps | grep postgres")
        print("")
        print("2. Start PostgreSQL container:")
        print("   docker start <container_name>")
        print("")
        print("3. Or start a new container (see above)")
    else:
        print(f"❌ Connection error: {error_msg}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Unexpected error: {e}")
    sys.exit(1)
EOF

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo "✅ Database connection test passed!"
    echo ""
    echo "You can now run migrations:"
    echo "  ./scripts/run_migrations.sh"
else
    echo ""
    echo "❌ Database connection test failed"
    echo "   Please fix the connection issue and try again"
fi

