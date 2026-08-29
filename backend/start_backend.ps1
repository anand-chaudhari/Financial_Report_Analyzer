# FinSight AI Backend - PowerShell Auto-Restart Daemon
$Host.UI.RawUI.WindowTitle = "FinSight AI Backend - Auto-Restart Daemon"
Set-Location -Path $PSScriptRoot

while ($true) {
    Write-Host "=========================================================" -ForegroundColor Cyan
    Write-Host " FinSight AI Backend starting on http://127.0.0.1:8000" -ForegroundColor Green
    Write-Host "=========================================================" -ForegroundColor Cyan
    
    & ".\.venv\Scripts\python.exe" run_server.py
    
    Write-Host "`n[Auto-Restart Guard] Backend stopped or crashed. Restarting in 2 seconds..." -ForegroundColor Yellow
    Start-Sleep -Seconds 2
}
