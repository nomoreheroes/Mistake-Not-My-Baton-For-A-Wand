param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('compile', 'test', 'validate')]
    [string]$Mode,

    [Parameter(Mandatory = $true)]
    [string]$EnvironmentRoot,

    [string]$OutputRoot
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$AllowedRoots = @(
    'C:\Users\Administrator\AppData\Local\Temp\2\pipeline-v2-k0b03-implementation-v1-A',
    'C:\Users\Administrator\AppData\Local\Temp\2\pipeline-v2-k0b03-implementation-v1-B'
)
$ResolvedEnvironment = [System.IO.Path]::GetFullPath($EnvironmentRoot).TrimEnd('\')
if ($AllowedRoots -notcontains $ResolvedEnvironment) {
    throw 'EnvironmentRoot is outside the closed K0b-03 set.'
}

$RepositoryRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\..'))
$Python = Join-Path $ResolvedEnvironment '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
    throw 'Pinned environment Python is missing.'
}

$env:PYTHONDONTWRITEBYTECODE = '1'
$env:PYTHONNOUSERSITE = '1'
$env:K0B03_ENV_ROOT = $ResolvedEnvironment.Replace('\', '/')
$env:TEMP = Join-Path $ResolvedEnvironment 'native-temp'
$env:TMP = $env:TEMP
$env:PYTHONPATH = $null

if ($Mode -in @('compile', 'validate')) {
    if ([string]::IsNullOrWhiteSpace($OutputRoot)) {
        throw 'OutputRoot is required for compile and validate.'
    }
    $ResolvedOutput = [System.IO.Path]::GetFullPath($OutputRoot)
    $WorkRoot = [System.IO.Path]::GetFullPath((Join-Path $ResolvedEnvironment 'work'))
    if (-not $ResolvedOutput.StartsWith($WorkRoot + '\', [System.StringComparison]::OrdinalIgnoreCase)) {
        throw 'OutputRoot must be below the exact environment work root.'
    }
    & $Python -B (Join-Path $RepositoryRoot 'new pipeline\harness\k0b03_v1\cli.py') compile --repository-root $RepositoryRoot --output-root $ResolvedOutput
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

if ($Mode -in @('test', 'validate')) {
    & $Python -B -m unittest discover -s (Join-Path $RepositoryRoot 'new pipeline\tests\k0b03_v1') -p 'test_*.py' -v
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

exit 0
