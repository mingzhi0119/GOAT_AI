param(
    [Parameter(Mandatory = $true)]
    [string]$Command,
    [string]$RepoPath = (Get-Location).Path,
    [string]$Distro = $env:GOAT_WSL_DISTRO
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if (-not (Get-Command wsl.exe -ErrorAction SilentlyContinue)) {
    throw "WSL is required for Linux-targeted commands in this repository, but wsl.exe was not found."
}

$resolvedRepoPath = (Resolve-Path -LiteralPath $RepoPath).Path
$normalizedRepoPath = $resolvedRepoPath -replace "\\", "/"
$wslRepoPath = (& wsl.exe wslpath -a $normalizedRepoPath).Trim()
if (-not $wslRepoPath) {
    throw "Failed to convert Windows path '$resolvedRepoPath' into a WSL path."
}

$wslArgs = @()
if ($Distro) {
    $wslArgs += "-d"
    $wslArgs += $Distro
}

$wslArgs += "bash"
$wslArgs += "-lc"
$wslArgs += "cd '$wslRepoPath' && $Command"

& wsl.exe @wslArgs
exit $LASTEXITCODE
