# UnR daily scan using Friday's data (Yahoo Finance).
# Run from backend/: .\scripts\run_friday_scan.ps1
# Optional: pass Friday date, e.g. .\scripts\run_friday_scan.ps1 2025-03-07

param([string]$AsOf = "2025-03-07")

$BackendRoot = if ($PSScriptRoot) { Split-Path $PSScriptRoot } else { "." }
Set-Location $BackendRoot

$Py = $null
try { $null = & python -c "pass" 2>&1; if ($LASTEXITCODE -eq 0) { $Py = "python" } } catch {}
if (-not $Py) { try { $null = & py -3 -c "pass" 2>&1; if ($LASTEXITCODE -eq 0) { $Py = "py -3" } } catch {} }
if (-not $Py) { Write-Host "Python not found. Run install.ps1 from repo root first."; exit 1 }

$OutFile = "watchlist_$AsOf.json"
if ($Py -eq "py -3") { & py -3 -m scanner.cli --yahoo --as-of $AsOf -o $OutFile }
else { & python -m scanner.cli --yahoo --as-of $AsOf -o $OutFile }
Write-Host "Watchlist saved to $OutFile"
