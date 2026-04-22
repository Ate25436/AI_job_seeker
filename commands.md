# Local Commands

## Backend

Run from a new PowerShell terminal:

```powershell
cd "C:\Users\KojimaK\Documents\Python Scripts\AI_job_seeker\backend"
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Backend API:

```text
http://localhost:8000
```

API docs:

```text
http://localhost:8000/docs
```

## Frontend

Run from another PowerShell terminal:

```powershell
cd "C:\Users\KojimaK\Documents\Python Scripts\AI_job_seeker\frontend"
npm run dev
```

Frontend:

```text
http://localhost:3000
```

## Rebuild Vector DB

Run this after changing files under `information_source/`.
`OPENAI_API_KEY` is read from `.env`.

```powershell
cd "C:\Users\KojimaK\Documents\Python Scripts\AI_job_seeker\backend"
..\.venv\Scripts\python.exe initialize_db.py --source ..\information_source --db-path ..\chroma_db
```
