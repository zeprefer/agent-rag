# Batch 7: Enterprise Hardening

## Implemented

- Celery worker for asynchronous document indexing.
- Redis-backed Celery broker and result backend.
- Structured JSON logging.
- Request ID response header and request access logs.
- Redis-backed fixed-window rate limiting.
- HTTP security headers.
- Upload security scanning for knowledge documents and chat attachments.
- Docker Compose worker service.
- Docker Compose API healthcheck.
- Local deployment and healthcheck scripts.

## Async Indexing

The existing endpoint remains:

```http
POST /api/v1/admin/documents/{document_id}/index
```

It now creates a `document_processing_jobs` record and enqueues `documents.index` in Celery. The admin UI should refresh index jobs to observe status changes.

Worker command:

```powershell
docker compose logs -f worker
```

## Rate Limiting

Environment variables:

```env
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS_PER_MINUTE=120
```

The limiter uses Redis and keys by Authorization header hash when present, otherwise by client IP and path.

## Security Scan

Environment variable:

```env
SECURITY_SCAN_ENABLED=true
```

The scanner rejects:

- EICAR test content.
- File signature mismatch for supported binary formats.
- PDF JavaScript/OpenAction/Launch/embedded file markers.
- Macro-enabled Office files.
- Office packages containing executable content.

## Deployment

Local deployment:

```powershell
.\scripts\deploy-local.ps1 -AdminEmail admin@example.com -AdminPassword "ChangeMe123!" -TenantName "Demo Enterprise"
```

Healthcheck:

```powershell
.\scripts\healthcheck.ps1
```

