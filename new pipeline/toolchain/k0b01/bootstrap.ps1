[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Target,
    [Parameter(Mandatory = $true)]
    [string]$Wheelhouse,
    [Parameter(Mandatory = $true)]
    [string]$HostPython
)

$ErrorActionPreference = 'Stop'
$ExpectedPythonHash = '6965927a96b81d1717c1d2186de7feb9b29ebf8775464020ebc2f25de6ef8ee0'

function Get-LowerSha256 {
    param([Parameter(Mandatory = $true)][string]$LiteralPath)
    return (Get-FileHash -Algorithm SHA256 -LiteralPath $LiteralPath).Hash.ToLowerInvariant()
}

$targetPath = [IO.Path]::GetFullPath($Target)
$wheelhousePath = [IO.Path]::GetFullPath($Wheelhouse)
$hostPythonPath = [IO.Path]::GetFullPath($HostPython)
$scriptRoot = Split-Path -Parent $PSCommandPath
$lockPath = Join-Path $scriptRoot 'toolchain-lock-v1.json'
$requirementsPath = Join-Path $scriptRoot 'requirements-v1.lock'

if (-not (Test-Path -LiteralPath $hostPythonPath -PathType Leaf)) {
    throw 'HostPython must name an existing file.'
}
if ((Get-LowerSha256 $hostPythonPath) -ne $ExpectedPythonHash) {
    throw 'HostPython SHA-256 does not match the lock.'
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
if (-not (Test-Path -LiteralPath $wheelhousePath -PathType Container)) {
    throw 'Wheelhouse must name an existing directory.'
}
if (Test-Path -LiteralPath $targetPath) {
    $existingItems = @(Get-ChildItem -LiteralPath $targetPath -Force)
    if ($existingItems.Count -ne 0) {
        throw 'Target directory must be empty or absent.'
    }
}

$lock = Get-Content -LiteralPath $lockPath -Raw | ConvertFrom-Json
$wheelFiles = @(Get-ChildItem -LiteralPath $wheelhousePath -File)
if ($wheelFiles.Count -ne 12) {
    throw 'Wheelhouse must contain exactly twelve files.'
}
foreach ($property in $lock.packages.PSObject.Properties) {
    $item = $property.Value
    $wheelPath = Join-Path $wheelhousePath $item.wheel
    if (-not (Test-Path -LiteralPath $wheelPath -PathType Leaf)) {
        throw "Missing wheel: $($item.wheel)"
    }
    if ((Get-LowerSha256 $wheelPath) -ne $item.sha256) {
        throw "Wheel SHA-256 mismatch: $($item.wheel)"
    }
}
$knownNames = @($lock.packages.PSObject.Properties | ForEach-Object { $_.Value.wheel })
$extraFiles = @($wheelFiles | Where-Object { $_.Name -notin $knownNames })
if ($extraFiles.Count -ne 0) {
    throw 'Wheelhouse contains an unbound file.'
}

if (-not (Test-Path -LiteralPath $targetPath)) {
    New-Item -ItemType Directory -Path $targetPath | Out-Null
}
$processTemp = Join-Path $targetPath '.tmp'
New-Item -ItemType Directory -Path $processTemp | Out-Null
$oldTemp = $env:TEMP
$oldTmp = $env:TMP
$oldPipConfig = $env:PIP_CONFIG_FILE
$oldPipNoIndex = $env:PIP_NO_INDEX

try {
    $env:TEMP = $processTemp
    $env:TMP = $processTemp
    $env:PIP_CONFIG_FILE = [IO.Path]::Combine($processTemp, 'isolated-pip.ini')
    $env:PIP_NO_INDEX = '1'
    & $hostPythonPath -m venv $targetPath
    if ($LASTEXITCODE -ne 0) {
        throw 'Virtual environment creation failed.'
    }
    $environmentPython = Join-Path $targetPath 'Scripts\python.exe'
    & $environmentPython -m pip install `
        --isolated `
        --no-index `
        --find-links $wheelhousePath `
        --require-hashes `
        --no-cache-dir `
        --disable-pip-version-check `
        -r $requirementsPath
    if ($LASTEXITCODE -ne 0) {
        throw 'Offline locked package installation failed.'
    }
    $inventoryCode = "import importlib.metadata as m,json;names=['colorama','iniconfig','packaging','pip','pluggy','pygments','pytest','ruamel.yaml','ruamel.yaml.clib','ruff','setuptools','wheel'];print(json.dumps({name:m.version(name) for name in names},sort_keys=True,separators=(',',':')))"
    $installed = & $environmentPython -c $inventoryCode
    if ($LASTEXITCODE -ne 0) {
        throw 'Installed package inventory failed.'
    }
    [ordered]@{
        package_count = 12
        packages = ($installed | ConvertFrom-Json)
        profile_id = $lock.profile_id
        result = 'pass'
    } | ConvertTo-Json -Compress -Depth 4
}
finally {
    $env:TEMP = $oldTemp
    $env:TMP = $oldTmp
    $env:PIP_CONFIG_FILE = $oldPipConfig
    $env:PIP_NO_INDEX = $oldPipNoIndex
}
