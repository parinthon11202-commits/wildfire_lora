$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$dashboardDir = Join-Path $projectRoot 'wildfire-dashboard'

try {
  $running = Invoke-RestMethod -Uri 'http://127.0.0.1:4400/api/health' -TimeoutSec 2
  if ($running.local_lab) {
    Write-Host 'FG1 local lab is already running.'
    Write-Host 'Lab: http://127.0.0.1:4401'
    Write-Host 'Dashboard: http://127.0.0.1:4400'
    exit 0
  }
} catch {
  # Start a new local lab when the dedicated port has no running lab.
}

Push-Location -LiteralPath $dashboardDir
$previousApiUrl = $env:VITE_API_URL
try {
  $env:VITE_API_URL = '/api'
  npm.cmd run build
  if ($LASTEXITCODE -ne 0) { throw 'Dashboard build failed' }
} finally {
  if ($null -eq $previousApiUrl) { Remove-Item Env:VITE_API_URL -ErrorAction SilentlyContinue }
  else { $env:VITE_API_URL = $previousApiUrl }
  Pop-Location
}

node (Join-Path $projectRoot 'scripts/fg1-local-lab.js')
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
