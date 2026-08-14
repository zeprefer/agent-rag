$ErrorActionPreference = "Stop"

$targets = @(
    "http://localhost:8000/api/v1/health",
    "http://localhost:5173",
    "http://localhost:5174"
)

foreach ($target in $targets) {
    $response = Invoke-WebRequest -UseBasicParsing -Uri $target -TimeoutSec 5
    Write-Host "$target -> $($response.StatusCode)"
}

docker compose ps

