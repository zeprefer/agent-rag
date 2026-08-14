param(
    [string]$AdminEmail = "admin@example.com",
    [string]$AdminPassword = "ChangeMe123!",
    [string]$TenantName = "Demo Enterprise"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env from .env.example"
}

docker compose up --build -d
docker compose exec api alembic upgrade head

$createAdmin = "python -m app.cli create-admin --email `"$AdminEmail`" --password `"$AdminPassword`" --tenant-name `"$TenantName`" --if-not-exists"
docker compose exec api sh -lc $createAdmin

Write-Host "Deployment complete"
Write-Host "API: http://localhost:8000/docs"
Write-Host "Admin: http://localhost:5173"
Write-Host "User: http://localhost:5174"
Write-Host "Smoke test: .\scripts\smoke-docker.ps1 -CreateAdmin"
