# Batch 5: Admin Frontend Notes

## Location

The management console lives in:

- `frontend/admin/index.html`
- `frontend/admin/styles.css`
- `frontend/admin/app.js`

It is a zero-build static SPA. It can be opened by any static file server, and Docker Compose serves it through Nginx.

## Local Startup

With Docker Compose:

```powershell
Copy-Item .env.example .env
docker compose up --build
```

Open:

```text
http://localhost:5173
```

Without Docker, serve the static files:

```powershell
python -m http.server 5173 --directory frontend/admin
```

The default API base in the login form is:

```text
http://localhost:8000/api/v1
```

## Implemented Workflow

1. Admin signs in.
2. Admin creates or selects a knowledge base.
3. Admin uploads `.docx`, `.doc`, `.pdf`, or `.md`.
4. Admin triggers indexing on a document.
5. Admin refreshes index jobs.
6. Admin opens generated chunks for inspection.

## Backend Dependencies

The frontend expects these backend endpoints:

- `POST /api/v1/auth/login`
- `GET /api/v1/admin/knowledge-bases`
- `POST /api/v1/admin/knowledge-bases`
- `GET /api/v1/admin/knowledge-bases/{kb_id}/documents`
- `POST /api/v1/admin/knowledge-bases/{kb_id}/documents`
- `POST /api/v1/admin/documents/{document_id}/index`
- `GET /api/v1/admin/index-jobs`
- `GET /api/v1/admin/documents/{document_id}/chunks`

## Verification Performed

- JavaScript syntax check with Node `--check`.
- Static HTTP serving check for `index.html`, `app.js`, and `styles.css`.

Browser automation was not available in this environment: the exposed tool search did not provide an agent-browser callable, and the bundled Playwright package was missing `playwright-core`.

