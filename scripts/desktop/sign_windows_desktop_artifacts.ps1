param(
    [Parameter(Mandatory = $true)]
    [string]$BundleRoot,

    [Parameter(Mandatory = $true)]
    [string]$CertificateBase64,

    [Parameter(Mandatory = $true)]
    [string]$CertificatePassword,

    [string]$TimestampUrl = "http://timestamp.digicert.com",

    [string]$Description = "GOAT AI Desktop"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-SignToolPath {
    $direct = Get-Command signtool.exe -ErrorAction SilentlyContinue
    if ($null -ne $direct) {
        return $direct.Source
    }

    $windowsKitRoots = @(
        "C:\Program Files (x86)\Windows Kits\10\bin",
        "C:\Program Files\Microsoft SDKs\ClickOnce\SignTool"
    )

    foreach ($root in $windowsKitRoots) {
        if (-not (Test-Path -LiteralPath $root)) {
            continue
        }
        $match = Get-ChildItem -LiteralPath $root -Recurse -Filter signtool.exe -File |
            Sort-Object FullName -Descending |
            Select-Object -First 1
        if ($null -ne $match) {
            return $match.FullName
        }
    }

    throw "Could not locate signtool.exe on this runner."
}

function Get-InstallerTargets {
    param(
        [Parameter(Mandatory = $true)]
        [string]$BundleRootPath
    )

    $targets = @()
    $targets += Get-ChildItem -Path (Join-Path $BundleRootPath "msi") -Filter *.msi -File -ErrorAction Stop
    $targets += Get-ChildItem -Path (Join-Path $BundleRootPath "nsis") -Filter *-setup.exe -File -ErrorAction Stop

    if ($targets.Count -eq 0) {
        throw "No Windows installer artifacts found under $BundleRootPath."
    }

    return $targets
}

$resolvedBundleRoot = (Resolve-Path -LiteralPath $BundleRoot).Path
$signTool = Get-SignToolPath
$targets = Get-InstallerTargets -BundleRootPath $resolvedBundleRoot
$tempPfx = Join-Path ([System.IO.Path]::GetTempPath()) ("goat-desktop-signing-" + [System.Guid]::NewGuid().ToString("N") + ".pfx")

try {
    [System.IO.File]::WriteAllBytes($tempPfx, [Convert]::FromBase64String($CertificateBase64))

    $arguments = @(
        "sign",
        "/fd", "SHA256",
        "/td", "SHA256",
        "/tr", $TimestampUrl,
        "/f", $tempPfx,
        "/p", $CertificatePassword,
        "/d", $Description
    )
    $arguments += $targets.FullName

    & $signTool @arguments
    if ($LASTEXITCODE -ne 0) {
        throw "signtool sign failed with exit code $LASTEXITCODE."
    }

    foreach ($artifact in $targets) {
        $signature = Get-AuthenticodeSignature -FilePath $artifact.FullName
        if ($signature.Status -ne "Valid") {
            throw "Authenticode verification failed for $($artifact.FullName): $($signature.Status)"
        }
    }
}
finally {
    if (Test-Path -LiteralPath $tempPfx) {
        Remove-Item -LiteralPath $tempPfx -Force
    }
}
