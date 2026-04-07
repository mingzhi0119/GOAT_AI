param(
    [string]$ProjectDir = (Get-Location).Path,
    [string]$RepoUrl = "https://github.com/mingzhi0119/GOAT_AI.git",
    [string]$GitBranch = "main",
    [string]$PythonBin = "python",
    [switch]$Quick,
    [switch]$SkipBuild,
    [switch]$SyncGit
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

function Stop-PidFileProcess {
    param([string]$PidFile)
    if (-not (Test-Path -LiteralPath $PidFile)) {
        return
    }

    $rawPid = Get-Content -LiteralPath $PidFile -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($rawPid -and ($rawPid.ToString().Trim() -match '^\d+$')) {
        $pidValue = [int]$rawPid
        $proc = Get-Process -Id $pidValue -ErrorAction SilentlyContinue
        if ($null -ne $proc) {
            Stop-Process -Id $pidValue -Force -ErrorAction SilentlyContinue
            Start-Sleep -Seconds 1
        }
    }

    Remove-Item -LiteralPath $PidFile -Force -ErrorAction SilentlyContinue
}

function Stop-PortProcess {
    param([int]$Port)
    $connections = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    foreach ($connection in $connections) {
        if ($connection.OwningProcess -gt 0) {
            Stop-Process -Id $connection.OwningProcess -Force -ErrorAction SilentlyContinue
        }
    }
    Start-Sleep -Seconds 1
}

function Test-HealthPort {
    param([int]$Port)
    for ($i = 0; $i -lt 15; $i++) {
        try {
            Invoke-WebRequest -Uri "http://127.0.0.1:$Port/api/health" -UseBasicParsing | Out-Null
            return $true
        } catch {
            Start-Sleep -Seconds 1
        }
    }
    return $false
}

function Read-DotEnvValue {
    param(
        [string]$DotEnvPath,
        [string]$Name
    )

    if (-not (Test-Path -LiteralPath $DotEnvPath)) {
        return $null
    }

    foreach ($rawLine in Get-Content -LiteralPath $DotEnvPath -Encoding utf8) {
        $line = $rawLine.Trim()
        if (-not $line -or $line.StartsWith("#") -or -not $line.Contains("=")) {
            continue
        }

        $parts = $line.Split("=", 2)
        $key = $parts[0].Trim()
        if ($key -ne $Name) {
            continue
        }

        $value = $parts[1].Trim()
        if (
            $value.Length -ge 2 -and
            (
                ($value.StartsWith('"') -and $value.EndsWith('"')) -or
                ($value.StartsWith("'") -and $value.EndsWith("'"))
            )
        ) {
            return $value.Substring(1, $value.Length - 2)
        }

        return $value
    }

    return $null
}

function Test-OllamaEndpoint {
    param([string]$BaseUrl)
    try {
        Invoke-WebRequest -Uri ($BaseUrl.TrimEnd('/') + "/api/tags") -UseBasicParsing | Out-Null
        return $true
    } catch {
        return $false
    }
}

function Resolve-OllamaBaseUrl {
    param([string]$ProjectRoot)

    $explicitEnvUrl = $env:OLLAMA_BASE_URL
    if ($explicitEnvUrl -and $explicitEnvUrl.Trim()) {
        Write-Step "Respecting explicit OLLAMA_BASE_URL from environment: $explicitEnvUrl"
        return $explicitEnvUrl.Trim()
    }

    $dotEnvPath = Join-Path $ProjectRoot ".env"
    $explicitDotEnvUrl = Read-DotEnvValue -DotEnvPath $dotEnvPath -Name "OLLAMA_BASE_URL"
    if ($explicitDotEnvUrl -and $explicitDotEnvUrl.Trim()) {
        Write-Step "Respecting explicit OLLAMA_BASE_URL from .env: $explicitDotEnvUrl"
        return $explicitDotEnvUrl.Trim()
    }

    $defaultUrl = "http://127.0.0.1:11434"
    if (Test-OllamaEndpoint -BaseUrl $defaultUrl) {
        Write-Step "Using existing local Ollama at $defaultUrl"
        return $defaultUrl
    }

    Assert-CommandAvailable -Name ollama
    $ollamaOutLog = Join-Path $ProjectRoot "ollama.local.out.log"
    $ollamaErrLog = Join-Path $ProjectRoot "ollama.local.err.log"

    Write-Step "Starting local Ollama on $defaultUrl"
    $ollamaProcess = Start-Process `
        -FilePath "ollama" `
        -ArgumentList @("serve") `
        -RedirectStandardOutput $ollamaOutLog `
        -RedirectStandardError $ollamaErrLog `
        -WindowStyle Hidden `
        -PassThru

    for ($i = 0; $i -lt 20; $i++) {
        if (Test-OllamaEndpoint -BaseUrl $defaultUrl) {
            Write-Step "Local Ollama is ready on $defaultUrl (PID $($ollamaProcess.Id))"
            return $defaultUrl
        }
        Start-Sleep -Seconds 1
    }

    throw "OLLAMA_BASE_URL was not explicitly configured, and deploy.ps1 could not reach or start Ollama on $defaultUrl. Check $ollamaOutLog and $ollamaErrLog."
}

function Get-ResolvedTargetPorts {
    param([string]$PythonExe)
    $output = & $PythonExe -m goat_ai.runtime_target --ordered-ports
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to resolve deployment target ports."
    }

    return @($output | ForEach-Object { $_.ToString().Trim() } | Where-Object { $_ })
}

$ProjectDir = [System.IO.Path]::GetFullPath($ProjectDir)
$VenvDir = Join-Path $ProjectDir ".venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
$FrontendDir = Join-Path $ProjectDir "frontend"
$ApiLog = Join-Path $ProjectDir "fastapi.log"
$ApiErrLog = Join-Path $ProjectDir "fastapi.err.log"
$ApiPid = Join-Path $ProjectDir "fastapi.pid"
$QuickLabel = if ($Quick.IsPresent) { " [QUICK mode]" } else { "" }
$ResolvedOllamaBaseUrl = $null

Write-Host "GOAT AI Windows deploy starting (branch: $GitBranch)$QuickLabel"

Assert-CommandAvailable -Name git
Assert-CommandAvailable -Name $PythonBin
Assert-CommandAvailable -Name npm

if (-not (Test-Path -LiteralPath (Join-Path $ProjectDir ".git"))) {
    Write-Step "Cloning repository into $ProjectDir"
    git clone $RepoUrl $ProjectDir
}

Set-Location -LiteralPath $ProjectDir
git checkout $GitBranch

if ($SyncGit.IsPresent) {
    Write-Step "Syncing to origin/$GitBranch"
    git fetch --all --prune
    git reset --hard "origin/$GitBranch"
} else {
    Write-Step "Deploying current local checkout on $GitBranch (SYNC_GIT=0)"
}

if ($Quick.IsPresent) {
    Write-Step "Skipping Python venv / pip install"
    if (-not (Test-Path -LiteralPath $VenvPython)) {
        throw "Venv not found at $VenvDir. Run deploy.ps1 without -Quick first."
    }
} else {
    if (-not (Test-Path -LiteralPath $VenvPython)) {
        Write-Step "Creating virtualenv at $VenvDir"
        & $PythonBin -m venv $VenvDir
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to create virtualenv at $VenvDir"
        }
    }

    Write-Step "Installing Python dependencies"
    & $VenvPython -m pip install --upgrade pip --quiet
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to upgrade pip inside $VenvDir"
    }
    & $VenvPython -m pip install -r requirements.txt --quiet
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to install Python requirements."
    }
}

if ($SkipBuild.IsPresent -and (Test-Path -LiteralPath (Join-Path $FrontendDir "dist"))) {
    Write-Step "Skipping npm build because -SkipBuild was provided and dist exists"
} else {
    Write-Step "Installing Node dependencies with npm ci"
    Push-Location -LiteralPath $FrontendDir
    try {
        npm ci --silent
        if ($LASTEXITCODE -ne 0) {
            throw "npm ci failed"
        }

        Write-Step "Building React frontend"
        npm run build
        if ($LASTEXITCODE -ne 0) {
            throw "npm run build failed"
        }
    } finally {
        Pop-Location
    }
}

$ResolvedOllamaBaseUrl = Resolve-OllamaBaseUrl -ProjectRoot $ProjectDir

$TargetPorts = Get-ResolvedTargetPorts -PythonExe $VenvPython
if ($TargetPorts.Count -eq 0) {
    throw "No deployment target ports were resolved."
}

$SelectedPort = $null
Stop-PidFileProcess -PidFile $ApiPid

foreach ($candidatePortText in $TargetPorts) {
    $candidatePort = [int]$candidatePortText
    Write-Step "Trying FastAPI on port $candidatePort"

    Stop-PortProcess -Port $candidatePort
    Stop-PidFileProcess -PidFile $ApiPid

    $startupArgs = @(
        "-m", "uvicorn",
        "server:app",
        "--host", "0.0.0.0",
        "--port", $candidatePort.ToString(),
        "--workers", "2"
    )

    $startInfo = @{
        FilePath = $VenvPython
        ArgumentList = $startupArgs
        WorkingDirectory = $ProjectDir
        RedirectStandardOutput = $ApiLog
        RedirectStandardError = $ApiErrLog
        WindowStyle = "Hidden"
        PassThru = $true
    }

    $previousGoatPort = $env:GOAT_PORT
    $previousOllamaBaseUrl = $env:OLLAMA_BASE_URL
    try {
        $env:GOAT_PORT = $candidatePort.ToString()
        $env:OLLAMA_BASE_URL = $ResolvedOllamaBaseUrl
        $process = Start-Process @startInfo
    } finally {
        $env:GOAT_PORT = $previousGoatPort
        $env:OLLAMA_BASE_URL = $previousOllamaBaseUrl
    }

    Set-Content -LiteralPath $ApiPid -Value $process.Id -Encoding utf8

    if (Test-HealthPort -Port $candidatePort) {
        $SelectedPort = $candidatePort
        break
    }

    Stop-PidFileProcess -PidFile $ApiPid
}

if ($null -eq $SelectedPort) {
    throw "FastAPI did not become healthy on any resolved target port: $($TargetPorts -join ', ')"
}

$stopPidText = if (Test-Path -LiteralPath $ApiPid) {
    (Get-Content -LiteralPath $ApiPid -ErrorAction SilentlyContinue | Select-Object -First 1)
} else {
    "<missing pid file>"
}

Write-Host ""
Write-Host "GOAT AI deployment complete"
Write-Host "API health: http://127.0.0.1:$SelectedPort/api/health"
Write-Host "OLLAMA_BASE_URL: $ResolvedOllamaBaseUrl"
Write-Host "FastAPI log: $ApiLog"
Write-Host "FastAPI err: $ApiErrLog"
Write-Host "Stop command: Stop-Process -Id $stopPidText"
