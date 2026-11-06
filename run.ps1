$ErrorActionPreference = 'Stop'
$runtime = $env:CAMPUS_PYTHON
if (-not $runtime) {
    $bundledRuntime = Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
    if (Test-Path -LiteralPath $bundledRuntime) { $runtime = $bundledRuntime }
    else { $runtime = 'python' }
}
& $runtime (Join-Path $PSScriptRoot 'manage.py') @args
exit $LASTEXITCODE
