[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet(
        'bootstrap',
        'validate',
        'test',
        'lint',
        'format-check',
        'render',
        'check',
        'validate-budget'
    )]
    [string]$Command,
    [string]$PythonPath,
    [string]$Wheelhouse,
    [string]$Target,
    [string]$HostPython,
    [string]$EvidencePath
)

$ErrorActionPreference = 'Stop'
$OutputEncoding = New-Object System.Text.UTF8Encoding($false)
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
$scriptRoot = Split-Path -Parent $PSCommandPath
$env:PYTHONPATH = $null
$ownedPythonFiles = @(
    (Join-Path $scriptRoot 'test_budget_evidence.py'),
    (Join-Path $scriptRoot 'test_toolchain.py'),
    (Join-Path $scriptRoot 'validate_budget_evidence.py'),
    (Join-Path $scriptRoot 'validate_toolchain.py')
)

function Stop-InvalidInput {
    param([Parameter(Mandatory = $true)][string]$Reason)
    [ordered]@{
        command = $Command
        error = $Reason
        exit_code = 2
        result = 'invalid_input'
    } | ConvertTo-Json -Compress
    exit 2
}

switch ($Command) {
    'bootstrap' {
        if (-not $Target -or -not $Wheelhouse -or -not $HostPython) {
            Stop-InvalidInput 'Target, Wheelhouse, and HostPython are required.'
        }
        & (Join-Path $scriptRoot 'bootstrap.ps1') `
            -Target $Target `
            -Wheelhouse $Wheelhouse `
            -HostPython $HostPython
        exit $LASTEXITCODE
    }
    'validate' {
        if (-not $PythonPath -or -not $Wheelhouse) {
            Stop-InvalidInput 'PythonPath and Wheelhouse are required.'
        }
        & $PythonPath -I `
            (Join-Path $scriptRoot 'validate_toolchain.py') `
            --toolchain-root $scriptRoot `
            --wheelhouse $Wheelhouse
        exit $LASTEXITCODE
    }
    'lint' {
        if (-not $PythonPath) {
            Stop-InvalidInput 'PythonPath is required.'
        }
        $ruffPath = Join-Path (Split-Path -Parent $PythonPath) 'ruff.exe'
        if (-not (Test-Path -LiteralPath $ruffPath -PathType Leaf)) {
            Stop-InvalidInput 'The locked Ruff executable is unavailable.'
        }
        & $ruffPath check --isolated --no-cache $ownedPythonFiles
        exit $LASTEXITCODE
    }
    'format-check' {
        if (-not $PythonPath) {
            Stop-InvalidInput 'PythonPath is required.'
        }
        $ruffPath = Join-Path (Split-Path -Parent $PythonPath) 'ruff.exe'
        if (-not (Test-Path -LiteralPath $ruffPath -PathType Leaf)) {
            Stop-InvalidInput 'The locked Ruff executable is unavailable.'
        }
        & $ruffPath format --check --isolated --no-cache $ownedPythonFiles
        exit $LASTEXITCODE
    }
    'test' {
        if (-not $PythonPath) {
            Stop-InvalidInput 'PythonPath is required.'
        }
        $oldPluginAutoload = $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD
        try {
            $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'
            & $PythonPath -I -m pytest `
                -p no:cacheprovider `
                (Join-Path $scriptRoot 'test_toolchain.py') `
                (Join-Path $scriptRoot 'test_budget_evidence.py')
            exit $LASTEXITCODE
        }
        finally {
            $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = $oldPluginAutoload
        }
    }
    'validate-budget' {
        if (-not $PythonPath -or -not $EvidencePath) {
            Stop-InvalidInput 'PythonPath and EvidencePath are required.'
        }
        & $PythonPath -I `
            (Join-Path $scriptRoot 'validate_budget_evidence.py') `
            --evidence $EvidencePath
        exit $LASTEXITCODE
    }
    'render' {
        '{"command":"render","exit_code":3,"result":"prerequisite_not_materialized"}'
        exit 3
    }
    'check' {
        '{"command":"check","exit_code":3,"result":"prerequisite_not_materialized"}'
        exit 3
    }
}
