[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Wheelhouse,
    [Parameter(Mandatory = $true)]
    [string]$HostPython
)

$ErrorActionPreference = 'Stop'
$ExpectedPythonHash = '6965927a96b81d1717c1d2186de7feb9b29ebf8775464020ebc2f25de6ef8ee0'
$ExpectedPowerShellHash = '38f4384643b3fa0de714d2367b712c2e0fa1c89e2cfd131ae6b831ad962b1033'
$IndexUrl = 'https://pypi.org/simple'
$Pins = @(
    'pip==24.2',
    'setuptools==75.1.0',
    'wheel==0.44.0',
    'ruamel.yaml==0.18.6',
    'ruamel.yaml.clib==0.2.8',
    'pytest==9.0.2',
    'ruff==0.15.1',
    'colorama==0.4.6',
    'iniconfig==1.1.1',
    'packaging==24.1',
    'pluggy==1.6.0',
    'pygments==2.15.1'
)

function Get-LowerSha256 {
    param([Parameter(Mandatory = $true)][string]$LiteralPath)
    return (Get-FileHash -Algorithm SHA256 -LiteralPath $LiteralPath).Hash.ToLowerInvariant()
}

$hostPythonPath = [IO.Path]::GetFullPath($HostPython)
$wheelhousePath = [IO.Path]::GetFullPath($Wheelhouse)
$scriptRoot = Split-Path -Parent $PSCommandPath
$lockPath = Join-Path $scriptRoot 'toolchain-lock-v1.json'

if (-not (Test-Path -LiteralPath $hostPythonPath -PathType Leaf)) {
    throw 'HostPython must name an existing file.'
}
if ((Get-LowerSha256 $hostPythonPath) -ne $ExpectedPythonHash) {
    throw 'HostPython SHA-256 does not match the lock.'
}
if ($PSVersionTable.PSVersion.ToString() -ne '5.1.20348.4294') {
    throw 'PowerShell version does not match the lock.'
}
$powerShellPath = (Get-Process -Id $PID).Path
if ((Get-LowerSha256 $powerShellPath) -ne $ExpectedPowerShellHash) {
    throw 'PowerShell executable SHA-256 does not match the lock.'
}
$runtimeLines = @(& $hostPythonPath -c 'import platform,sys;print(platform.machine().upper());print(platform.python_implementation());print(sys.platform);print(platform.python_version())')
if ($LASTEXITCODE -ne 0) {
    throw 'HostPython metadata probe failed.'
}
if ($runtimeLines.Count -ne 4 -or
    $runtimeLines[0] -ne 'AMD64' -or
    $runtimeLines[1] -ne 'CPython' -or
    $runtimeLines[2] -ne 'win32' -or
    $runtimeLines[3] -ne '3.12.7') {
    throw 'Host runtime or platform does not match the lock.'
}
if (Test-Path -LiteralPath $wheelhousePath) {
    throw 'Wheelhouse target must be absent.'
}

$lock = Get-Content -LiteralPath $lockPath -Raw | ConvertFrom-Json
New-Item -ItemType Directory -Path $wheelhousePath | Out-Null
$pipTemp = Join-Path $wheelhousePath 'pip-temp'
New-Item -ItemType Directory -Path $pipTemp | Out-Null
$oldTemp = $env:TEMP
$oldTmp = $env:TMP

try {
    $env:TEMP = $pipTemp
    $env:TMP = $pipTemp
    foreach ($pin in $Pins) {
        & $hostPythonPath -m pip download `
            --no-deps `
            --only-binary=:all: `
            --no-cache-dir `
            --disable-pip-version-check `
            --progress-bar off `
            --index-url $IndexUrl `
            --dest $wheelhousePath `
            $pin
        if ($LASTEXITCODE -ne 0) {
            throw "Wheel download failed for $pin."
        }
    }

    $wheelFiles = @(Get-ChildItem -LiteralPath $wheelhousePath -File)
    if ($wheelFiles.Count -ne 12) {
        throw 'Wheelhouse must contain exactly twelve files.'
    }
    $report = @()
    foreach ($property in ($lock.packages.PSObject.Properties | Sort-Object Name)) {
        $item = $property.Value
        $wheelPath = Join-Path $wheelhousePath $item.wheel
        if (-not (Test-Path -LiteralPath $wheelPath -PathType Leaf)) {
            throw "Missing wheel: $($item.wheel)"
        }
        $actualHash = Get-LowerSha256 $wheelPath
        if ($actualHash -ne $item.sha256) {
            throw "Wheel SHA-256 mismatch: $($item.wheel)"
        }
        $report += [ordered]@{
            name = $property.Name
            sha256 = $actualHash
            size_bytes = (Get-Item -LiteralPath $wheelPath).Length
            wheel = $item.wheel
        }
    }
    $knownNames = @($lock.packages.PSObject.Properties | ForEach-Object { $_.Value.wheel })
    $extraFiles = @($wheelFiles | Where-Object { $_.Name -notin $knownNames })
    if ($extraFiles.Count -ne 0) {
        throw 'Wheelhouse contains an unbound file.'
    }

    $resolvedPipTemp = [IO.Path]::GetFullPath($pipTemp)
    $requiredPrefix = $wheelhousePath + [IO.Path]::DirectorySeparatorChar
    if (-not $resolvedPipTemp.StartsWith(
            $requiredPrefix,
            [StringComparison]::OrdinalIgnoreCase
        )) {
        throw 'pip temporary path escaped the wheelhouse.'
    }
    if ([IO.Path]::GetFileName($resolvedPipTemp) -ne 'pip-temp') {
        throw 'Unexpected pip temporary directory leaf.'
    }
    Remove-Item -LiteralPath $resolvedPipTemp -Recurse -Force
    [ordered]@{
        profile_id = $lock.profile_id
        result = 'pass'
        wheel_count = $report.Count
        wheels = $report
    } | ConvertTo-Json -Compress -Depth 5
}
finally {
    $env:TEMP = $oldTemp
    $env:TMP = $oldTmp
}
