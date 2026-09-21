[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$PythonPath,
    [Parameter(Mandatory=$true)][ValidateSet('validate-inputs','compile-all','init-db','audit-db','unittest','ruff-check','ruff-format')][string]$Mode,
    [Parameter(Mandatory=$true)][string]$RepositoryRoot,
    [Parameter(Mandatory=$true)][string]$Manifest,
    [Parameter(Mandatory=$true)][string]$RuntimeRoot,
    [Parameter(Mandatory=$true)][ValidateSet('environment_A','environment_B')][string]$Environment,
    [string]$OutputDir,
    [string]$Database,
    [int]$TargetVersion = 6,
    [string[]]$TestPaths = @()
)
$ErrorActionPreference = 'Stop'
function Assert-AbsolutePath {
    param([Parameter(Mandatory=$true)][string]$Value,[Parameter(Mandatory=$true)][string]$Name)
    if (-not [IO.Path]::IsPathRooted($Value) -or $Value -match '^[A-Za-z]:[^\\/]') {
        throw ($Name + ' must be absolute')
    }
}
Assert-AbsolutePath -Value $PythonPath -Name 'PythonPath'
Assert-AbsolutePath -Value $RepositoryRoot -Name 'RepositoryRoot'
Assert-AbsolutePath -Value $Manifest -Name 'Manifest'
Assert-AbsolutePath -Value $RuntimeRoot -Name 'RuntimeRoot'
$entry = Join-Path $RepositoryRoot 'new pipeline/harness/k0b02_v1/cli.py'
if ($Mode -eq 'unittest') {
    if ($TestPaths.Count -eq 0) { throw 'TestPaths required' }
    & $PythonPath -I -B -m unittest -v @TestPaths
    exit $LASTEXITCODE
}
if ($Mode -eq 'ruff-check' -or $Mode -eq 'ruff-format') {
    $ruff = Join-Path (Split-Path $PythonPath -Parent) 'ruff.exe'
    if ($Mode -eq 'ruff-check') { & $ruff check --no-cache @TestPaths }
    else { & $ruff format --check --no-cache @TestPaths }
    exit $LASTEXITCODE
}
$argsList = @($entry,$Mode,'--repository-root',$RepositoryRoot,'--manifest',$Manifest,'--runtime-root',$RuntimeRoot,'--environment',$Environment)
if ($OutputDir) { $argsList += @('--output-dir',$OutputDir) }
if ($Database) { $argsList += @('--database',$Database) }
$argsList += @('--target-version',[string]$TargetVersion)
& $PythonPath -I -B @argsList
exit $LASTEXITCODE
