Write-Host "=== FinAI dev (Windows / PowerShell) ==="
Write-Host "Starting backend (FastAPI) and frontend (Next.js) as background jobs..."
Write-Host ""

$apiJob = Start-Job -ScriptBlock {
    Set-Location "apps/api"
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
}

$webJob = Start-Job -ScriptBlock {
    Set-Location "apps/web"
    npm run dev
}

Write-Host "Backend job Id : $($apiJob.Id)"
Write-Host "Frontend job Id: $($webJob.Id)"
Write-Host ""
Write-Host "Use the following commands in this PowerShell session to manage jobs:"
Write-Host "  Get-Job                      # list jobs"
Write-Host "  Receive-Job -Id $($apiJob.Id)   # stream backend logs"
Write-Host "  Receive-Job -Id $($webJob.Id)   # stream frontend logs"
Write-Host "  Stop-Job -Id <Id>           # stop a job"
Write-Host ""
Write-Host "Press Ctrl+C to stop waiting; services will keep running as background jobs."

Wait-Job -Id $apiJob.Id, $webJob.Id