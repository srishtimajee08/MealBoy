$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$mealboyPython = Join-Path $PSScriptRoot '.venv-ml\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $mealboyPython)) {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        & py -3.12 -m venv .venv-ml
    } else {
        & python -c "import sys; assert sys.version_info[:2] == (3, 12), 'Install Python 3.12 first.'"
        if ($LASTEXITCODE -ne 0) { throw 'Python 3.12 is required.' }
        & python -m venv .venv-ml
    }
    if ($LASTEXITCODE -ne 0) { throw 'Install Python 3.12, then run this script again.' }
}
& $mealboyPython -m pip install -r requirements-ml.lock.txt
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed. Check the network and package output.' }
Write-Host 'Setup complete. Run .\run_mealboy.ps1 and open http://127.0.0.1:5000'
