param(
    [string]$ProjectDir = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\..")),
    [string]$PythonBin = "python",
    [switch]$Quick
)

$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host "==> $Message"
}

function Assert-CommandAvailable {
    param([string]$Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command '$Name' was not found on PATH."
    }
}

function Import-DotEnvIfPresent {
    param([string]$DotEnvPath)

    if (-not (Test-Path -LiteralPath $DotEnvPath)) {
        return
    }

    foreach ($rawLine in Get-Content -LiteralPath $DotEnvPath -Encoding utf8) {
        $line = $rawLine.Trim()
        if (-not $line -or $line.StartsWith("#") -or -not $line.Contains("=")) {
            continue
        }

        $parts = $line.Split("=", 2)
        $key = $parts[0].Trim()
        $value = $parts[1].Trim()
        if (
            $value.Length -ge 2 -and
            (
                ($value.StartsWith('"') -and $value.EndsWith('"')) -or
                ($value.StartsWith("'") -and $value.EndsWith("'"))
            )
        ) {
            $value = $value.Substring(1, $value.Length - 2)
        }
        Set-Item -Path "Env:$key" -Value $value
    }
}

$ProjectDir = [System.IO.Path]::GetFullPath($ProjectDir)
$VenvDir = Join-Path $ProjectDir ".venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
$FrontendDir = Join-Path $ProjectDir "frontend"
$DotEnvPath = Join-Path $ProjectDir ".env"
$previousGoatDeployMode = $env:GOAT_DEPLOY_MODE

Write-Host "GOAT AI local Windows build starting"

Assert-CommandAvailable -Name git
Assert-CommandAvailable -Name $PythonBin
Assert-CommandAvailable -Name npm

Write-Step "Loading local environment"
Import-DotEnvIfPresent -DotEnvPath $DotEnvPath

try {
    $env:GOAT_DEPLOY_MODE = "0"

    Write-Step "Python virtualenv and dependencies"
    if ($Quick.IsPresent) {
        Write-Step "Skipping Python venv / pip install"
        if (-not (Test-Path -LiteralPath $VenvPython)) {
            throw "Venv not found at $VenvDir. Run build_local.ps1 without -Quick first."
        }
    } else {
        if (-not (Test-Path -LiteralPath $VenvPython)) {
            & $PythonBin -m venv $VenvDir
            if ($LASTEXITCODE -ne 0) {
                throw "Failed to create virtualenv at $VenvDir"
            }
        }

        & $VenvPython -m pip install --upgrade pip --quiet
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to upgrade pip inside $VenvDir"
        }
        & $VenvPython -m pip install -r (Join-Path $ProjectDir "requirements.txt") --quiet
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to install Python requirements."
        }
    }

    Write-Step "Frontend dependencies and build"
    Push-Location -LiteralPath $FrontendDir
    try {
        npm ci --silent
        if ($LASTEXITCODE -ne 0) {
            throw "npm ci failed"
        }

        npm run build
        if ($LASTEXITCODE -ne 0) {
            throw "npm run build failed"
        }
    } finally {
        Pop-Location
    }

    Write-Step "Config validation"
    Push-Location -LiteralPath $ProjectDir
    try {
        & $VenvPython -c "from goat_ai.config.settings import load_settings; s = load_settings(); print(f'GOAT_DEPLOY_MODE={s.deploy_mode} ({s.deploy_mode_name})')"
        if ($LASTEXITCODE -ne 0) {
            throw "Config validation failed."
        }
    } finally {
        Pop-Location
    }
} finally {
    $env:GOAT_DEPLOY_MODE = $previousGoatDeployMode
}

Write-Host ""
Write-Host "GOAT AI local Windows build complete"
Write-Host "Frontend bundle: $FrontendDir\\dist"
Write-Host "Python venv:     $VenvDir"
