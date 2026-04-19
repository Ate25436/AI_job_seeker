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

Game flow support on Render:
- frontend から backend の `/api/game/start`, `/api/game/ask`, `/api/game/end`, `/api/game/score`, `/api/game/result/{session_id}` を呼び出す
- 面接ゲームは frontend と backend の両サービスがそろって初めて成立するため、CORS_ALLOW_ORIGINS と NEXT_PUBLIC_API_BASE_URL を必ず対で更新する
- `game/result` を含む面接フロー確認をデプロイ後の疎通確認に含める

Re-index endpoint:
```bash
curl -X POST https://your-backend.onrender.com/api/admin/reindex \
  -H "X-Admin-Token: your-token"
```

Markdown を更新後の re-index 手順:
1. `information_source/` の markdown を更新する
2. 変更をデプロイする
3. `POST /api/admin/reindex` を呼び出してベクタDBを再構築する
4. re-index 後に面接画面から質問し、更新した markdown が回答に反映されるか確認する

```bash
curl -X POST https://your-backend.onrender.com/api/admin/reindex \
  -H "X-Admin-Token: ${REINDEX_TOKEN}"
```

シナリオ追加手順:
1. `scenarios/` に YAML を追加する
2. 必要なら `information_source/` に関連 markdown を追加する
3. Render デプロイ後に `/api/game/start` の `scenario_file` で新シナリオを指定して起動確認する
4. 面接終了後に `/api/game/result/{session_id}` まで通して動作確認する

本番のセッション保存方針:
- 現在の実装は `GameSessionService` のインメモリ保持で、短時間の面接ゲームを前提にする
- 本番での session persistence は Redis などの外部ストアへ移す前提で、少なくとも `session_id`, 開始時刻, 終了時刻, 会話履歴, submitted_scores, 結果スナップショットを保存対象にする
- Render の複数インスタンスや再起動をまたぐ用途ではインメモリのまま運用しない

ログ出力方針:
- backend はアクセスログ、ステータスコード、処理時間、re-index 実行、ゲームフローの失敗を記録する
- frontend は個人情報を残さず、画面エラーと API 失敗を最小限に追跡する
- logging strategy として、質問本文や機微情報は本番ログにそのまま書かない

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
