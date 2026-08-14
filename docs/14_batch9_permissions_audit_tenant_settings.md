# Batch 9: Enterprise Permissions, Audit, and Tenant Settings

This batch adds tenant-level governance capabilities to the enterprise admin console and backend.

## Backend

Added RBAC permissions:

- `admin`: full tenant administration
- `manager`: knowledge base and document administration
- `user`: user chat access

Added API endpoints:

- `GET /api/v1/admin/roles`
- `GET /api/v1/admin/users`
- `POST /api/v1/admin/users`
- `PATCH /api/v1/admin/users/{user_id}`
- `DELETE /api/v1/admin/users/{user_id}`
- `GET /api/v1/admin/audit-logs`
- `GET /api/v1/admin/tenant-settings`
- `PATCH /api/v1/admin/tenant-settings`

Added database tables:

- `tenant_settings`
- `audit_logs`

Added migration:

- `backend/alembic/versions/0006_rbac_audit_tenant_settings.py`

## Runtime Behavior

- Knowledge-base administration endpoints now require `knowledge:manage`, so both `admin` and `manager` can manage enterprise knowledge.
- User management, audit logs, and tenant settings require `admin`.
- Login, user changes, knowledge base changes, document uploads, indexing requests, and tenant setting changes create audit logs.
- Tenant settings now affect upload validation:
  - enterprise document extensions
  - enterprise document max upload size
  - chat attachment max upload size

## Admin Frontend

The admin console now shows governance sections for `admin` users:

- Users
- Roles
- Tenant Settings
- Audit Logs

`manager` users can still use knowledge-base and document administration, but governance panels are hidden.

## Verification

Run migrations:

```powershell
docker compose exec api alembic upgrade head
```

Open the admin console:

```text
http://localhost:5173
```

Recommended checks:

- Login as `admin@example.com`.
- Create a `manager` user.
- Login as the manager and confirm knowledge management works but governance panels are hidden.
- Login as admin again and confirm audit logs show user creation and knowledge operations.
- Change tenant upload settings and verify unsupported extensions are rejected.
