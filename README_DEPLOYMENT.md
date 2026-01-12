# AI Job Seeker Deployment

This project converts the existing Python RAG system into a web application with FastAPI backend and React/Next.js frontend.

## Project Structure

```
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py         # FastAPI application entry point
│   │   ├── models.py       # Pydantic models
│   │   ├── config.py       # Configuration management
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   └── routes.py   # API route definitions
│   │   └── services/       # Business logic services
│   │       └── __init__.py
│   ├── requirements.txt    # Python dependencies
│   ├── .env.example       # Environment variables template
│   └── Dockerfile.dev     # Development Docker configuration
├── frontend/               # Next.js frontend
│   ├── src/
│   │   ├── app/           # Next.js app directory
│   │   ├── components/    # React components (to be created)
│   │   ├── lib/          # Utility libraries
│   │   └── types/        # TypeScript type definitions
│   ├── package.json      # Node.js dependencies
│   ├── next.config.js    # Next.js configuration
│   ├── tsconfig.json     # TypeScript configuration
│   ├── tailwind.config.js # Tailwind CSS configuration
│   └── Dockerfile.dev    # Development Docker configuration
├── docker-compose.dev.yml # Development environment
├── .env.example          # Global environment variables
└── README_DEPLOYMENT.md  # This file
```

## Development Setup

1. Copy environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your OpenAI API key
   ```

2. Start development environment:
   ```bash
   docker-compose -f docker-compose.dev.yml up --build
   ```

3. Access the application:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

## Manual Setup (Alternative)

### Backend Setup
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your configuration
uvicorn app.main:app --reload
```

### Frontend Setup
```bash
cd frontend
npm install
cp .env.local.example .env.local
# Edit .env.local with your configuration
npm run dev
```

## Production-like Docker Setup

```bash
docker-compose up --build
```

This uses `backend/Dockerfile` and `frontend/Dockerfile` and mounts `chroma_db/` and `information_source/`.

## Cloud Deployment (Render)

Render uses `render.yaml` at the repo root to provision both services.

Backend (Render):
- Service name: `ai-job-seeker-backend`
- Root directory: `backend`
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Environment variables:
  - `OPENAI_API_KEY`
  - `ENVIRONMENT=production`
  - `CHROMA_DB_PATH=/var/data/chroma_db`
  - `INFO_SOURCE_PATH=/opt/render/project/src/information_source`
  - `AUTO_INIT_VECTOR_DB=true` (optional)
  - `CORS_ALLOW_ORIGINS=https://your-frontend.onrender.com`
  - `REINDEX_TOKEN` (required if you want to use the re-index endpoint)

Frontend (Render):
- Service name: `ai-job-seeker-frontend`
- Root directory: `frontend`
- Environment variables:
  - `NEXT_PUBLIC_API_BASE_URL=https://your-backend.onrender.com`

Re-index endpoint:
```bash
curl -X POST https://your-backend.onrender.com/api/admin/reindex \
  -H "X-Admin-Token: your-token"
```

## Vector Database Utilities

Initialize from markdown sources:
```bash
cd backend
python initialize_db.py --source ../information_source --db-path ./chroma_db
```

Backup the database:
```bash
python scripts/backup_vector_db.py --db-path ./chroma_db --output-dir backups
```

Restore the database:
```bash
python scripts/restore_vector_db.py backups/chroma_db_backup_YYYYMMDD_HHMMSS.zip --db-path ./chroma_db --force
```

## Next Steps

This setup provides the foundation for:
1. Refactoring existing RAG system into API service (Task 2)
2. Implementing FastAPI server endpoints (Task 3)
3. Building React frontend components (Task 5)
4. Environment configuration and security (Task 6)
5. Cloud deployment preparation (Tasks 8-11)

## Requirements Addressed

- **Requirement 2.1**: API Server structure for REST endpoints
- **Requirement 4.1**: Environment variable management setup
- **Requirement 4.2**: Secure configuration handling framework
