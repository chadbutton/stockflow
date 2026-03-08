# Launch UnR Watchlist backend (API) and frontend (dashboard) in separate windows.
# Run from repo root: .\launch_dashboard.ps1

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
if (-not $Root) { $Root = Get-Location }

$BackendDir = Join-Path $Root "backend"
$DashboardDir = Join-Path $Root "dashboard"
$UnrSetupDir = Join-Path $Root "unr_setup"
$LogPath = Join-Path $Root "debug-d56396.log"

function Write-DebugLog($obj) {
    $line = ($obj | ConvertTo-Json -Compress) -replace "`n"," "
    Add-Content -LiteralPath $LogPath -Value $line -ErrorAction SilentlyContinue
}

# #region agent log
Write-DebugLog @{ sessionId = "d56396"; location = "launch_dashboard.ps1:start"; message = "launch script started"; data = @{ root = $Root; backendDir = $BackendDir; unrSetupDir = $UnrSetupDir } ; timestamp = [long]([DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()); hypothesisId = "H1" }
# #endregion

if (-not (Test-Path $BackendDir)) { throw "Backend folder not found: $BackendDir" }
if (-not (Test-Path $DashboardDir)) { throw "Dashboard folder not found: $DashboardDir" }

# Start backend in a new window (pass log path for backend to write)
$BackendCmd = @"
`$env:PYTHONPATH = '$BackendDir;$UnrSetupDir'
`$env:DEBUG_LOG = '$LogPath'
Set-Location '$BackendDir'
Write-Host 'Installing unr_setup and backend deps...' -ForegroundColor Cyan
python -m pip install -e '$UnrSetupDir' -q
python -m pip install -e . -q
Write-Host 'Starting UnR API on http://localhost:8000' -ForegroundColor Cyan
python -m uvicorn server.app:app --reload --port 8000
"@
Start-Process powershell -ArgumentList "-NoExit", "-Command", $BackendCmd

# #region agent log
Write-DebugLog @{ sessionId = "d56396"; location = "launch_dashboard.ps1:backend_started"; message = "backend process started"; data = @{} ; timestamp = [long]([DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()); hypothesisId = "H2" }
# #endregion

# Wait for backend to be reachable (up to 30 seconds)
$ApiReady = $false
$MaxAttempts = 15
for ($i = 0; $i -lt $MaxAttempts; $i++) {
    Start-Sleep -Seconds 2
    try {
        $null = Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/dates" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
        $ApiReady = $true
        # #region agent log
        Write-DebugLog @{ sessionId = "d56396"; location = "launch_dashboard.ps1:api_ready"; message = "backend responded"; data = @{ attempt = $i + 1 } ; timestamp = [long]([DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()); hypothesisId = "H3" }
        # #endregion
        Write-Host "Backend is up." -ForegroundColor Green
        break
    } catch {
        # #region agent log
        Write-DebugLog @{ sessionId = "d56396"; location = "launch_dashboard.ps1:wait_attempt"; message = "wait attempt"; data = @{ attempt = $i + 1; error = $_.Exception.Message } ; timestamp = [long]([DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()); hypothesisId = "H4" }
        # #endregion
        Write-Host "Waiting for backend... ($($i + 1)/$MaxAttempts)" -ForegroundColor Yellow
    }
}
if (-not $ApiReady) {
    # #region agent log
    Write-DebugLog @{ sessionId = "d56396"; location = "launch_dashboard.ps1:timeout"; message = "backend did not respond in time"; data = @{} ; timestamp = [long]([DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()); hypothesisId = "H5" }
    # #endregion
    Write-Host "Backend did not respond in time. Check the backend window for errors (e.g. missing deps, wrong path). Starting frontend anyway." -ForegroundColor Yellow
}

# Start frontend in a new window
$FrontendCmd = @"
Set-Location '$DashboardDir'
Write-Host 'Starting dashboard on http://localhost:5173' -ForegroundColor Cyan
npm run dev
"@
Start-Process powershell -ArgumentList "-NoExit", "-Command", $FrontendCmd

Write-Host "Backend and frontend launched in separate windows."
Write-Host "  API:    http://localhost:8000"
Write-Host "  App:    http://localhost:5173"
Write-Host "Close either window to stop that process."
