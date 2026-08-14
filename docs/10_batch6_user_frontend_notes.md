# Batch 6: User Frontend Notes

## Location

The user chat console lives in:

- `frontend/user/index.html`
- `frontend/user/styles.css`
- `frontend/user/app.js`

It is a zero-build static SPA served by Docker Compose through Nginx.

## Local Startup

With Docker Compose:

```powershell
Copy-Item .env.example .env
docker compose up --build
```

Open:

```text
http://localhost:5174
```

Without Docker, serve the static files:

```powershell
python -m http.server 5174 --directory frontend/user
```

The default API base in the login form is:

```text
http://localhost:8000/api/v1
```

## Implemented Workflow

1. User signs in.
2. User creates or selects a chat session.
3. User optionally attaches files or images.
4. User sends a text question.
5. The frontend uploads attachments and sends their IDs with the question.
6. The backend performs RAG retrieval and generation.
7. The frontend renders the assistant answer.
8. The frontend renders citations with document title, page, heading, score, and quoted source text.

## Backend Dependencies

The frontend expects these backend endpoints:

- `POST /api/v1/auth/login`
- `POST /api/v1/chat/sessions`
- `GET /api/v1/chat/sessions`
- `GET /api/v1/chat/sessions/{session_id}/messages`
- `POST /api/v1/chat/sessions/{session_id}/attachments`
- `GET /api/v1/chat/sessions/{session_id}/attachments`
- `POST /api/v1/chat/sessions/{session_id}/messages`

## Current Scope

Batch 6 now supports text RAG chat with temporary user attachments. Uploaded attachments belong to the current chat session and do not enter the enterprise knowledge base.

Supported temporary files:

- `.docx`
- `.doc`
- `.pdf`
- `.md`
- `.txt`

Supported temporary images:

- `.png`
- `.jpg`
- `.jpeg`
- `.webp`
