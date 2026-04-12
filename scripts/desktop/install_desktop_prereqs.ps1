[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [ValidateSet('Runtime', 'Dev', 'All')]
    [string]$Profile = 'Runtime',

    [switch]$IncludeOllama
)

$ErrorActionPreference = 'Stop'

function Assert-Winget {
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        throw "winget is required but was not found on PATH."
    }
}

function Get-WingetInstalled {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Id
    )

    $output = winget list --id $Id -e --accept-source-agreements 2>$null
    return ($LASTEXITCODE -eq 0 -and ($output -match [regex]::Escape($Id)))
}

function Ensure-WingetPackage {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Id,

        [string]$Label = '',

        [string]$Override = ''
    )

    $name = if ($Label) { $Label } else { $Id }
    if (Get-WingetInstalled -Id $Id) {
        Write-Host "[skip] $name already installed"
        return
    }

    $args = @(
        'install',
        '--id', $Id,
        '-e',
        '--accept-source-agreements',
        '--accept-package-agreements',
        '--silent'
    )
    if ($Override) {
        $args += @('--override', $Override)
    }

    if ($PSCmdlet.ShouldProcess($name, 'Install via winget')) {
        Write-Host "[install] $name"
        & winget @args
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to install $name via winget."
        }
    }
}

Assert-Winget

$installRuntime = $Profile -in @('Runtime', 'All', 'Dev')
$installDev = $Profile -in @('Dev', 'All')
$shouldInstallOllama = $IncludeOllama.IsPresent -or $Profile -in @('Runtime', 'All')

if ($installRuntime) {
    Ensure-WingetPackage -Id 'Microsoft.EdgeWebView2Runtime' -Label 'Microsoft Edge WebView2 Runtime'
}

if ($installDev) {
    Ensure-WingetPackage -Id 'Rustlang.Rustup' -Label 'Rust toolchain (rustup)'
    Ensure-WingetPackage `
        -Id 'Microsoft.VisualStudio.2022.BuildTools' `
        -Label 'Visual Studio Build Tools 2022 (C++ workload)' `
        -Override '--quiet --wait --norestart --nocache --installPath C:\BuildTools --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended'
}

if ($shouldInstallOllama) {
    Ensure-WingetPackage -Id 'Ollama.Ollama' -Label 'Ollama'
}

Write-Host ''
Write-Host "Desktop prerequisite installation complete for profile: $Profile"
Write-Host "Runtime profile installs: WebView2$(if ($shouldInstallOllama) { ', Ollama' } else { '' })"
if ($installDev) {
    Write-Host 'Dev profile also installs: rustup, cargo/rustc, Visual Studio Build Tools 2022 (MSVC workload)'
}
