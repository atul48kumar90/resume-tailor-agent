# Resume Tailor Agent

A full-stack application for tailoring resumes to job descriptions with AI-powered ATS optimization.

## Project Structure

```
resume-tailor-agent/
├── backend/          # Python FastAPI backend
│   ├── api/          # API routes and endpoints
│   ├── agents/       # Business logic and AI agents
│   ├── core/         # Core utilities (LLM, caching, security)
│   ├── db/           # Database models and repositories
│   ├── scripts/      # Utility scripts
│   ├── tests/        # Test suite
│   └── workers/      # Background job workers
├── frontend/         # Frontend application (to be implemented)
└── .venv/            # Python virtual environment (at root)
```

## Quick Start

### Backend Setup

1. **Install dependencies:**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. **Set up environment variables:**
   ```bash
   # Copy .env.example to .env and fill in your values
   cp .env.example .env
   ```

3. **Set up database:**
   ```bash
   cd backend
   ./scripts/run_migrations.sh
   ```

4. **Start the API server:**
   ```bash
   cd backend
   ./scripts/start_api.sh
   ```

The API will be available at:
- API: http://localhost:8000
- Docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

### Frontend Setup

Frontend code will be developed in the `frontend/` directory.

## Development

### Running Tests

```bash
cd backend
pytest
```

### Running Scripts

All scripts are in `backend/scripts/`:
- `start_api.sh` - Start the API server
- `start_worker.sh` - Start background job workers
- `run_migrations.sh` - Run database migrations
- `test_all_endpoints.sh` - Test all API endpoints

## Documentation

See `backend/docs/` for detailed documentation:
- API documentation
- Database setup
- Security guidelines
- Anti-hallucination guide

## License

[Your License Here]

