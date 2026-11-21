# Experimental installer for a locally built Windows executable.
param([switch]$Quiet)
$ErrorActionPreference = 'Stop'

$source = Join-Path $PSScriptRoot 'STREONOR-MCP.exe'
if (-not (Test-Path -LiteralPath $source -PathType Leaf)) {
    throw 'Build STREONOR-MCP.exe and place it next to this script first.'
}

$app = Join-Path $env:LOCALAPPDATA 'STREONOR-MCP\app'
$exe = Join-Path $app 'STREONOR-MCP.exe'
New-Item -ItemType Directory -Force -Path $app | Out-Null
Copy-Item -LiteralPath $source -Destination $exe -Force

if (-not $Quiet) {
    Write-Output "Experimental executable installed at $exe"
    Write-Output 'For normal setup, use the package and stdio instructions in the README.'
}
