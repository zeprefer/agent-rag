# Backend

FastAPI backend for Enterprise Agent RAG.

## Local Docker Startup

```powershell
Copy-Item .env.example .env
docker compose up --build
```

Run database migrations:

```powershell
docker compose exec api alembic upgrade head
```

Create the first administrator:

```powershell
docker compose exec api python -m app.cli create-admin --email admin@example.com --password "ChangeMe123!" --tenant-name "Demo Enterprise"
```

Open API docs:

- http://localhost:8000/docs
- http://localhost:8000/api/v1/health

## Implemented In Batch 1

- FastAPI project structure
- Environment-based configuration
- PostgreSQL and Redis connectivity
- SQLAlchemy models for tenants and users
- Alembic initial migration
- JWT login
- Current-user endpoint
- Docker Compose for API, PostgreSQL, and Redis

## Implemented In Batch 2

- MinIO/S3-compatible object storage
- Knowledge base CRUD for administrators
- Document upload for `.docx`, `.doc`, `.pdf`, and `.md`
- Document and document-version records
- File size, file type, filename, and SHA256 validation
- Tenant-scoped admin APIs

## Implemented In Batch 3

- Document processing job records
- PDF text extraction with `pypdf`
- DOCX text and table extraction with `python-docx`
- DOC conversion through LibreOffice headless, then DOCX parsing
- Markdown heading-aware parsing
- Structure-aware chunking with page and heading metadata
- Bailian/DashScope OpenAI-compatible Embedding provider
- `knowledge_chunks` and `chunk_embeddings` tables backed by pgvector
- HNSW cosine index for vector search
- Manual indexing trigger and chunk inspection APIs

## Implemented In Batch 4

- Chat sessions and message history
- Tenant-scoped RAG retrieval over `knowledge_chunks`
- Query embedding with Bailian/DashScope
- pgvector cosine similarity retrieval
- Knowledge-base access filtering
- Prompt construction with numbered evidence blocks
- Bailian/DashScope OpenAI-compatible Chat provider
- Assistant answers with persisted citations

## Implemented In Batch 5

- Static admin SPA under `frontend/admin`
- Admin login against `/api/v1/auth/login`
- Knowledge base listing and creation
- Document upload against admin document APIs
- Manual indexing trigger
- Index job status display
- Chunk inspection view
- Nginx container for Docker Compose

## Implemented In Batch 6

- Static user SPA under `frontend/user`
- User login against `/api/v1/auth/login`
- Chat session list and creation
- Text question submission against `/api/v1/chat`
- Message history rendering
- Citation/source rendering for assistant answers
- Nginx container for Docker Compose

## Implemented After Batch 6: User Attachments

- Chat attachment upload endpoint
- Temporary file parsing for `.docx`, `.doc`, `.pdf`, `.md`, and `.txt`
- Temporary image understanding through Bailian/DashScope vision model
- Attachment context injection into RAG prompts
- User frontend attachment selection and upload flow

## Implemented In Batch 7

- Celery worker for asynchronous document indexing
- Redis-backed queue and result backend
- JSON request logging with request IDs
- Redis-backed rate limiting
- HTTP security headers
- Upload security scanner for documents and chat attachments
- API Docker healthcheck
- Local deployment and healthcheck scripts

## Useful API Paths

- `POST /api/v1/admin/knowledge-bases`
- `GET /api/v1/admin/knowledge-bases`
- `PATCH /api/v1/admin/knowledge-bases/{kb_id}`
- `DELETE /api/v1/admin/knowledge-bases/{kb_id}`
- `POST /api/v1/admin/knowledge-bases/{kb_id}/documents`
- `GET /api/v1/admin/knowledge-bases/{kb_id}/documents`
- `GET /api/v1/admin/documents/{document_id}`
- `POST /api/v1/admin/documents/{document_id}/index`
- `GET /api/v1/admin/index-jobs`
- `GET /api/v1/admin/documents/{document_id}/chunks`
- `POST /api/v1/chat/sessions`
- `GET /api/v1/chat/sessions`
- `GET /api/v1/chat/sessions/{session_id}/messages`
- `POST /api/v1/chat/sessions/{session_id}/attachments`
- `GET /api/v1/chat/sessions/{session_id}/attachments`
- `POST /api/v1/chat/sessions/{session_id}/messages`

## Operations

Start the full stack:

```powershell
.\scripts\deploy-local.ps1 -AdminEmail admin@example.com -AdminPassword "ChangeMe123!" -TenantName "Demo Enterprise"
```

Check services:

```powershell
.\scripts\healthcheck.ps1
```

Follow async worker logs:

```powershell
docker compose logs -f worker
```
