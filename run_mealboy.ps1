$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$mealboyPython = Join-Path $PSScriptRoot '.venv-ml\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $mealboyPython)) {
    throw 'Create the Python 3.12 ML environment and install requirements-ml.txt first.'
}
$env:KERAS_HOME = Join-Path $PSScriptRoot 'artifacts\keras-cache'
$env:MPLCONFIGDIR = Join-Path $PSScriptRoot 'artifacts\matplotlib-cache'
$mealboyTemp = Join-Path $PSScriptRoot 'artifacts\runtime-temp'
New-Item -ItemType Directory -Path $mealboyTemp -Force | Out-Null
$env:TEMP = $mealboyTemp
$env:TMP = $mealboyTemp
& $mealboyPython -m waitress --listen=127.0.0.1:5000 app:app
exit $LASTEXITCODE
