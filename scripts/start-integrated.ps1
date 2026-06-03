$Feeder = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Root = Split-Path -Parent $Feeder
$Alert = Join-Path $Root "onboard-alert"
$AlertBackend = Join-Path $Alert "backend"

Start-Process -FilePath (Join-Path $Feeder ".venv\Scripts\python.exe") `
  -ArgumentList @("-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8001") `
  -WorkingDirectory $Feeder `
  -WindowStyle Hidden

Start-Process -FilePath "npm.cmd" `
  -ArgumentList @("run", "dev") `
  -WorkingDirectory $AlertBackend `
  -WindowStyle Hidden

Start-Process -FilePath "npm.cmd" `
  -ArgumentList @("run", "dev", "--", "--host", "127.0.0.1", "--port", "5173") `
  -WorkingDirectory $Alert `
  -WindowStyle Hidden

Write-Host "Feeder:    http://127.0.0.1:8001"
Write-Host "Alert API: http://127.0.0.1:4000/health"
Write-Host "Alert UI:  http://127.0.0.1:5173"
