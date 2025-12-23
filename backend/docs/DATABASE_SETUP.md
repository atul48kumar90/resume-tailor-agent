# PostgreSQL Database Setup Guide

This application uses PostgreSQL for persistent data storage and Redis for caching/sessions.

## Architecture

- **PostgreSQL**: Stores persistent data (users, resumes, applications, job descriptions, jobs)
- **Redis**: Used for caching (JD analysis, resume rewrite, ATS scores) and rate limiting

## Quick Setup

### 1. Install PostgreSQL

**macOS:**
```bash
brew install postgresql
brew services start postgresql
```

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install postgresql postgresql-contrib
sudo systemctl start postgresql
```

**Windows:**
Download and install from [PostgreSQL Downloads](https://www.postgresql.org/download/windows/)

### 2. Create Database

```bash
# Connect to PostgreSQL
psql -U postgres

# Create database
CREATE DATABASE resume_tailor;

# Exit
\q
```

### 3. Configure Environment Variables

Create or update your `.env` file:

```bash
# PostgreSQL
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/resume_tailor
DATABASE_URL_SYNC=postgresql://postgres:postgres@localhost:5432/resume_tailor

# Database Pool Settings (optional)
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_TIMEOUT=30
DB_ECHO=false
```

### 4. Run Setup Script

```bash
./scripts/setup_database.sh
```

This script will:
- Check PostgreSQL installation
- Create the database if it doesn't exist
- Install dependencies
- Run database migrations

### 5. Manual Migration (Alternative)

If you prefer to run migrations manually:

```bash
# Install dependencies
pip install -r requirements.txt

# Run migrations
alembic upgrade head
```

## Database Models

### Users
- Stores user accounts (email, username)
- One-to-many relationship with resumes

### Resumes
- Stores resume metadata and content
- Tracks statistics (applications, interviews, ATS scores)
- One-to-many relationship with versions and applications

### Resume Versions
- Version control for resumes
- Tracks changes and maintains history

### Job Descriptions
- Stores analyzed job descriptions
- Caches LLM analysis results

### Applications
- Tracks resume applications to jobs
- Stores ATS scores and skill gap analysis
- Links resumes to job descriptions

### Jobs
- Background job tracking
- Stores job status and results

## Migration Commands

```bash
# Create a new migration
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View migration history
alembic history

# Show current revision
alembic current
```

## Fallback Behavior

The application is designed to gracefully handle database unavailability:

1. **PostgreSQL Primary**: All persistent data operations use PostgreSQL
2. **Redis Fallback**: If PostgreSQL is unavailable, some operations fall back to Redis (with TTL)
3. **Cache Always Redis**: Caching operations always use Redis

## Troubleshooting

### Connection Errors

If you see connection errors:

1. **Check PostgreSQL is running:**
   ```bash
   pg_isready
   ```

2. **Verify connection string:**
   ```bash
   psql -U postgres -h localhost -d resume_tailor
   ```

3. **Check firewall/network:**
   - Ensure PostgreSQL is listening on the correct port (default: 5432)
   - Check firewall rules if connecting remotely

### Migration Errors

If migrations fail:

1. **Check database exists:**
   ```bash
   psql -U postgres -l | grep resume_tailor
   ```

2. **Reset database (⚠️ DESTRUCTIVE):**
   ```bash
   # Drop and recreate
   psql -U postgres -c "DROP DATABASE resume_tailor;"
   psql -U postgres -c "CREATE DATABASE resume_tailor;"
   alembic upgrade head
   ```

3. **Check Alembic version table:**
   ```bash
   psql -U postgres -d resume_tailor -c "SELECT * FROM alembic_version;"
   ```

## Production Considerations

1. **Connection Pooling**: Already configured via SQLAlchemy
2. **Backups**: Set up regular PostgreSQL backups
3. **Monitoring**: Monitor database performance and connection pool usage
4. **Indexes**: Already created on frequently queried columns
5. **Security**: Use strong passwords and restrict database access

## Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@localhost:5432/resume_tailor` | Async database URL |
| `DATABASE_URL_SYNC` | `postgresql://postgres:postgres@localhost:5432/resume_tailor` | Sync database URL (for migrations) |
| `DB_POOL_SIZE` | `10` | Connection pool size |
| `DB_MAX_OVERFLOW` | `20` | Maximum overflow connections |
| `DB_POOL_TIMEOUT` | `30` | Connection timeout in seconds |
| `DB_ECHO` | `false` | Log SQL queries (useful for debugging) |

