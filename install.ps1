# Install project (unr_setup + backend). Run from repo root: .\install.ps1
$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
if (-not $Root) { $Root = Get-Location }

# Find Python: try python, then py -3
$Python = $null
try {
    $null = & python -c "pass" 2>&1
    if ($LASTEXITCODE -eq 0) { $Python = "python" }
} catch {}
if (-not $Python) {
    try {
        $null = & py -3 -c "pass" 2>&1
        if ($LASTEXITCODE -eq 0) { $Python = "py -3" }
    } catch {}
}
if (-not $Python) {
    Write-Host "Python not found. If you already installed Python:"
    Write-Host "  1. Close and reopen this terminal."
    Write-Host "  2. Try: py -3 -m pip install -e unr_setup"
    Write-Host "     then: py -3 -m pip install -e backend"
    Write-Host "  3. Or turn off App execution aliases for python.exe (Settings > Apps > App execution aliases)."
    Write-Host "See INSTALL.md for more."
    exit 1
}

Write-Host "Using: $Python"
Set-Location $Root

function Run-Pip {
    if ($Python -eq "py -3") {
        & py -3 -m pip @args
    } else {
        & python -m pip @args
    }
}

# Order matters: backend depends on unr-setup
Write-Host "Installing unr_setup..."
Run-Pip install --upgrade pip -q
Run-Pip install -e "$Root\unr_setup"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Installing backend..."
Run-Pip install -e "$Root\backend"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Done. Run Friday scan: cd backend; $Python -m scanner.cli --yahoo --as-of 2025-03-07 -o watchlist.json"
exit 0
