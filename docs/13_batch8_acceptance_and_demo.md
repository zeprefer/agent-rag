# Batch 8: Acceptance and Demo Loop

This batch turns the project into a repeatable local acceptance environment.

## Added

- Docker smoke test script: `scripts/smoke-docker.ps1`
- Demo enterprise knowledge document: `docs/demo/enterprise_policy.md`
- Idempotent admin creation flag: `python -m app.cli create-admin --if-not-exists`

## Basic Docker Acceptance

Use this mode when you want to verify containers, migrations, JWT login, knowledge base CRUD, document upload, object storage, and async job creation.

```powershell
Copy-Item .env.example .env
docker compose up --build -d
docker compose exec api alembic upgrade head
.\scripts\smoke-docker.ps1 -CreateAdmin
```

This mode does not require `DASHSCOPE_API_KEY`. The indexing worker may mark the job as failed later if no API key is configured, but the platform wiring is still verified.

## Full RAG Acceptance

Use this mode when `.env` contains a valid Alibaba Bailian/DashScope API key.

```powershell
.\scripts\smoke-docker.ps1 -CreateAdmin -RunModelChecks
```

The script will:

- wait for `/api/v1/ready`
- login as the admin user
- create a demo knowledge base
- upload `docs/demo/enterprise_policy.md`
- enqueue document indexing
- wait for indexing to complete
- verify chunks were generated
- create a chat session
- ask a question against the indexed knowledge base
- print the assistant answer and citation count

## Manual Demo URLs

- API docs: `http://localhost:8000/docs`
- Admin console: `http://localhost:5173`
- User console: `http://localhost:5174`
- MinIO console: `http://localhost:9001`

## Acceptance Criteria

- `docker compose ps` shows `api`, `worker`, `postgres`, `redis`, `minio`, `admin`, and `user` running.
- `/api/v1/ready` returns database and Redis as `ok`.
- Admin login succeeds.
- Demo knowledge base is created.
- Demo Markdown document is uploaded and versioned.
- Indexing job is created asynchronously.
- With a valid DashScope key, indexing completes and chunks are visible.
- With a valid DashScope key, user chat returns an answer with citations.
