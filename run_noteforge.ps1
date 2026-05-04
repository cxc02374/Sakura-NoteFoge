$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$py = Join-Path (Split-Path -Parent $root) '.venv\Scripts\python.exe'
if (-not (Test-Path $py)) {
    Write-Error "Python not found: $py"
    exit 1
}

Set-Location $root
& $py -m pip install -r (Join-Path $root 'requirements.txt') | Out-Null
Start-Process -FilePath $py -ArgumentList @('-m', 'noteforge.main') -WorkingDirectory $root
