# Batch 10: Agent Configuration and Runtime Policy

This batch adds a real enterprise Agent configuration layer on top of the RAG system.

## Backend

Added database model and migration:

- `agents`
- `chat_sessions.agent_id`
- `backend/alembic/versions/0007_agent_configuration.py`

Added admin APIs:

- `GET /api/v1/admin/agents`
- `POST /api/v1/admin/agents`
- `GET /api/v1/admin/agents/{agent_id}`
- `PATCH /api/v1/admin/agents/{agent_id}`
- `DELETE /api/v1/admin/agents/{agent_id}`

Added user API:

- `GET /api/v1/agents`

Only published Agents are available to user chat sessions.

## Agent Runtime Policy

Each Agent can configure:

- system prompt
- default knowledge base scope
- chat model override
- temperature
- retrieval `top_k`
- max context tokens
- draft/published/archived lifecycle

When a user creates a chat session with an Agent, RAG uses the Agent policy for retrieval and answer generation. Existing behavior remains compatible: sessions without `agent_id` use the default enterprise assistant policy.

## Admin Frontend

The admin console now includes an Agents panel for `admin` and `manager` users.

Managers can:

- create Agents
- bind default knowledge bases
- set prompt and RAG policy
- publish or archive Agents

Agent create/update/archive actions are written to audit logs.

## User Frontend

The user console now loads published Agents and lets the user choose one before creating a new chat session.

## Verification

Run:

```powershell
docker compose exec api alembic upgrade head
```

Then:

- Open `http://localhost:5173`
- Create and publish an Agent in the admin console
- Open `http://localhost:5174`
- Select the published Agent
- Create a new chat and ask a question
- Inspect the assistant message metadata in API responses to confirm the Agent policy was used
