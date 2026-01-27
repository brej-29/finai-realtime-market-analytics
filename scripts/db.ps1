Param(
    [ValidateSet("up", "down", "migrate", "seed")]
    [string]$Action = "up"
)

Write-Host "=== FinAI DB helper (Windows / PowerShell) ==="
Write-Host "Action: $Action"
Write-Host ""

switch ($Action) {
    "up" {
        Write-Host "Starting local Postgres via docker-compose..."
        docker-compose up -d db
    }
    "down" {
        Write-Host "Stopping local Postgres container..."
        docker-compose stop db
    }
    "migrate" {
        Write-Host "Applying Alembic migrations..."
        Push-Location "apps/api"
        try {
            alembic upgrade head
        } finally {
            Pop-Location
        }
    }
    "seed" {
        Write-Host "No DB seed script is defined yet; nothing to do."
    }
}

Write-Host ""
Write-Host "Done."