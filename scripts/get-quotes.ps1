# Desktop-friendly launcher for q-quotes-fetcher (Windows PowerShell).
# Runs from wherever it lives, passing all arguments through.
$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Error "error: 'uv' not found on PATH. Install it from https://docs.astral.sh/uv/"
    exit 1
}

Push-Location $Root
try {
    uv run get-passages @args
} finally {
    Pop-Location
}

Write-Host ""
Read-Host "Press Enter to close..."