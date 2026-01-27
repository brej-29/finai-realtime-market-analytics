Param(
    [switch]$SkipFrontend
)

Write-Host "=== FinAI setup (Windows / PowerShell) ==="

# Backend: Python dependencies
Write-Host "`n[1/2] Installing backend dependencies (apps/api)..."
Push-Location "apps/api"
try {
    python -m pip install --upgrade pip
    pip install -r requirements.txt
} finally {
    Pop-Location
}

if (-not $SkipFrontend) {
    # Frontend: Node dependencies
    Write-Host "`n[2/2] Installing frontend dependencies (apps/web)..."
    Push-Location "apps/web"
    try {
        npm install
    } finally {
        Pop-Location
    }
}

Write-Host "`nSetup complete."
Write-Host "You can now start the stack with:"
Write-Host "  - .\scripts\dev.ps1           # start backend + frontend"
Write-Host "  - or: make api / make web    # on WSL / Git Bash"