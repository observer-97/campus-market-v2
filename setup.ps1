$ErrorActionPreference = 'Stop'
$runtime = $env:CAMPUS_PYTHON
if (-not $runtime) {
    $bundledRuntime = Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
    if (Test-Path -LiteralPath $bundledRuntime) { $runtime = $bundledRuntime }
    else { $runtime = 'python' }
}
& $runtime -c "import sys; assert (3,11) <= sys.version_info[:2] <= (3,13), 'Please use Python 3.12 (3.11-3.13 supported)'"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $runtime -m pip install --target (Join-Path $PSScriptRoot '.packages312') -r (Join-Path $PSScriptRoot 'requirements.txt')
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
foreach ($command in @('migrate', 'train_model', 'init_demo', 'check')) {
    & $runtime (Join-Path $PSScriptRoot 'manage.py') $command
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
