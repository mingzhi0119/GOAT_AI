param(
    [string]$ProjectDir = (Get-Location).Path,
    [string]$RepoUrl = "https://github.com/mingzhi0119/GOAT_AI.git",
    [string]$GitBranch = "main",
    [string]$GitRef = $GitBranch,
    [string]$ExpectedGitSha = $env:EXPECTED_GIT_SHA,
    [string]$ReleaseBundle = $env:RELEASE_BUNDLE,
    [string]$ReleaseManifest = $env:RELEASE_MANIFEST,
    [string]$PythonBin = "python",
    [switch]$Quick,
    [switch]$SkipBuild,
    [switch]$SyncGit
)

$ErrorActionPreference = "Stop"
$Script:RepoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\.."))

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
            Stop-Process -Id $pidValue -ErrorAction SilentlyContinue
            for ($attempt = 0; $attempt -lt 30; $attempt++) {
                if (-not (Get-Process -Id $pidValue -ErrorAction SilentlyContinue)) {
                    break
                }
                Start-Sleep -Seconds 1
            }

            if (Get-Process -Id $pidValue -ErrorAction SilentlyContinue) {
                Write-Step "Graceful shutdown timed out for PID $pidValue; forcing cleanup."
                Stop-ProcessTree -ProcessId $pidValue
                Stop-ProcessTreeTaskkill -ProcessId $pidValue
            }
        }
    }

    Remove-Item -LiteralPath $PidFile -Force -ErrorAction SilentlyContinue
}

function Stop-ProcessTree {
    param([int]$ProcessId)

    $children = Get-CimInstance Win32_Process -Filter "ParentProcessId = $ProcessId" -ErrorAction SilentlyContinue
    foreach ($child in $children) {
        Stop-ProcessTree -ProcessId $child.ProcessId
    }

    $proc = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
    if ($null -ne $proc) {
        Stop-Process -Id $ProcessId -Force -ErrorAction SilentlyContinue
        Start-Sleep -Milliseconds 300
    }
}

function Stop-ProcessTreeTaskkill {
    param([int]$ProcessId)

    if ($ProcessId -le 0) {
        return
    }

    $taskkillExe = Join-Path $env:SystemRoot "System32\taskkill.exe"
    if (Test-Path -LiteralPath $taskkillExe) {
        & $taskkillExe /PID $ProcessId /T /F | Out-Null
    }
}

function Clear-PortOrFail {
    param(
        [int]$Port,
        [int]$MaxPasses = 8
    )

    for ($attempt = 0; $attempt -lt $MaxPasses; $attempt++) {
        $connections = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
        if (-not $connections) {
            return
        }

        $owners = @(
            $connections |
                Select-Object -ExpandProperty OwningProcess -Unique |
                Where-Object { $_ -gt 0 }
        )

        if (-not $owners) {
            throw "Port $Port is occupied, but no user-mode owning process was found."
        }

        $kernelOwners = @($owners | Where-Object { $_ -in @(0, 4) })
        if ($kernelOwners.Count -gt 0) {
            throw "Port $Port is occupied by a system/kernel-managed process: $($kernelOwners -join ', ')"
        }

        foreach ($ownerProcessId in $owners) {
            Stop-ProcessTree -ProcessId $ownerProcessId
            Stop-ProcessTreeTaskkill -ProcessId $ownerProcessId
        }

        Start-Sleep -Seconds 1
    }

    $remaining = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if ($remaining) {
        $stillListening = @(
            $remaining |
                Select-Object -ExpandProperty OwningProcess -Unique |
                Where-Object { $_ -gt 0 }
        )

        $kernelOwners = @($stillListening | Where-Object { $_ -in @(0, 4) })
        if ($kernelOwners.Count -gt 0) {
            throw "Port $Port is occupied by a system/kernel-managed process: $($kernelOwners -join ', ')"
        }

        throw "Port $Port is still occupied after forced cleanup: $($stillListening -join ', ')"
    }
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

function Test-DeploymentContract {
    param([int]$Port)

    if (-not (Test-HealthPort -Port $Port)) {
        return $false
    }

    try {
        $openApi = Invoke-WebRequest -Uri "http://127.0.0.1:$Port/openapi.json" -UseBasicParsing
        if ($openApi.StatusCode -ne 200) {
            return $false
        }
        return $openApi.Content -match '"/api/models/capabilities"'
    } catch {
        return $false
    }
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
    $runtimeRoot = if ($env:GOAT_RUNTIME_ROOT) {
        $env:GOAT_RUNTIME_ROOT
    } else {
        Join-Path $ProjectRoot "var"
    }
    $logsDir = if ($env:GOAT_LOG_DIR) {
        $env:GOAT_LOG_DIR
    } else {
        Join-Path $runtimeRoot "logs"
    }
    New-Item -ItemType Directory -Path $logsDir -Force | Out-Null
    $ollamaOutLog = Join-Path $logsDir "ollama.local.out.log"
    $ollamaErrLog = Join-Path $logsDir "ollama.local.err.log"

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

function Assert-ExpectedGitSha {
    param([string]$ExpectedSha)

    $normalized = $ExpectedSha.Trim()
    if (-not $normalized) {
        return
    }

    $currentSha = (& git rev-parse HEAD).Trim()
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to resolve current Git SHA for validation."
    }

    if ($currentSha -ne $normalized) {
        throw "Resolved SHA $currentSha did not match EXPECTED_GIT_SHA $normalized"
    }
}

function Sync-RequestedGitRef {
    param(
        [string]$Ref,
        [string]$ExpectedSha
    )

    git fetch --all --prune --tags
    if ($LASTEXITCODE -ne 0) {
        throw "git fetch failed while syncing $Ref"
    }

    git show-ref --verify --quiet "refs/remotes/origin/$Ref"
    if ($LASTEXITCODE -eq 0) {
        Write-Step "Syncing branch ref to origin/$Ref"
        git checkout --detach "origin/$Ref"
        if ($LASTEXITCODE -ne 0) {
            throw "git checkout failed for origin/$Ref"
        }
        git reset --hard "origin/$Ref"
        if ($LASTEXITCODE -ne 0) {
            throw "git reset --hard failed for origin/$Ref"
        }
    } else {
        $resolvedSha = (& git rev-parse --verify "$($Ref)^{commit}").Trim()
        if ($LASTEXITCODE -ne 0 -or -not $resolvedSha) {
            throw "git rev-parse failed for requested ref $Ref"
        }
        Write-Step "Syncing immutable ref $Ref ($resolvedSha)"
        git checkout --detach $resolvedSha
        if ($LASTEXITCODE -ne 0) {
            throw "git checkout failed for immutable ref $Ref"
        }
        git reset --hard $resolvedSha
        if ($LASTEXITCODE -ne 0) {
            throw "git reset --hard failed for immutable ref $Ref"
        }
    }

    Assert-ExpectedGitSha -ExpectedSha $ExpectedSha
}

$ProjectDir = [System.IO.Path]::GetFullPath($ProjectDir)
$VenvDir = Join-Path $ProjectDir ".venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
$FrontendDir = Join-Path $ProjectDir "frontend"
$RuntimeRoot = if ($env:GOAT_RUNTIME_ROOT) {
    $env:GOAT_RUNTIME_ROOT
} else {
    Join-Path $ProjectDir "var"
}
$LogsDir = if ($env:GOAT_LOG_DIR) {
    $env:GOAT_LOG_DIR
} else {
    Join-Path $RuntimeRoot "logs"
}
$LogDbPath = if ($env:GOAT_LOG_PATH) {
    $env:GOAT_LOG_PATH
} else {
    Join-Path $RuntimeRoot "chat_logs.db"
}
$DataDir = if ($env:GOAT_DATA_DIR) {
    $env:GOAT_DATA_DIR
} else {
    Join-Path $RuntimeRoot "data"
}
$ApiLog = Join-Path $LogsDir "fastapi.log"
$ApiErrLog = Join-Path $LogsDir "fastapi.err.log"
$ApiPid = Join-Path $LogsDir "fastapi.pid"
$ServerPort = 62606
$QuickLabel = if ($Quick.IsPresent) { " [QUICK mode]" } else { "" }
$ResolvedOllamaBaseUrl = $null
$BundleDeploy = -not [string]::IsNullOrWhiteSpace($ReleaseBundle)
$SkipBuildEffective = $SkipBuild.IsPresent -or $BundleDeploy

Write-Host "GOAT AI Windows deploy starting (branch: $GitBranch, ref: $GitRef)$QuickLabel"

Assert-CommandAvailable -Name git
Assert-CommandAvailable -Name $PythonBin
Assert-CommandAvailable -Name npm

if ($BundleDeploy) {
    if ([string]::IsNullOrWhiteSpace($ReleaseManifest)) {
        throw "RELEASE_MANIFEST is required when RELEASE_BUNDLE is set."
    }

    Write-Step "Installing immutable release bundle into $ProjectDir"
    New-Item -ItemType Directory -Path $ProjectDir -Force | Out-Null
    $previousManifestTemp = $null
    $currentManifestPath = Join-Path $ProjectDir "release-manifest.json"
    if (Test-Path -LiteralPath $currentManifestPath) {
        $previousManifestTemp = [System.IO.Path]::GetTempFileName()
        Copy-Item -LiteralPath $currentManifestPath -Destination $previousManifestTemp -Force
    }

    & $PythonBin (Join-Path $Script:RepoRoot "tools\release\install_release_bundle.py") `
        --bundle $ReleaseBundle `
        --manifest $ReleaseManifest `
        --project-dir $ProjectDir `
        --expected-sha $ExpectedGitSha
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to install immutable release bundle."
    }

    if ($previousManifestTemp) {
        Copy-Item `
            -LiteralPath $previousManifestTemp `
            -Destination (Join-Path $ProjectDir "release-manifest.previous.json") `
            -Force
        Remove-Item -LiteralPath $previousManifestTemp -Force -ErrorAction SilentlyContinue
    }
    Copy-Item -LiteralPath $ReleaseManifest -Destination $currentManifestPath -Force
} else {
    if (-not (Test-Path -LiteralPath (Join-Path $ProjectDir ".git"))) {
        Write-Step "Cloning repository into $ProjectDir"
        git clone $RepoUrl $ProjectDir
    }
}

Set-Location -LiteralPath $ProjectDir
New-Item -ItemType Directory -Path $RuntimeRoot -Force | Out-Null
New-Item -ItemType Directory -Path $LogsDir -Force | Out-Null
New-Item -ItemType Directory -Path $DataDir -Force | Out-Null

if (-not $BundleDeploy) {
    if ($SyncGit.IsPresent) {
        Sync-RequestedGitRef -Ref $GitRef -ExpectedSha $ExpectedGitSha
    } else {
        git checkout $GitRef
        if ($LASTEXITCODE -ne 0) {
            throw "git checkout failed for requested ref $GitRef"
        }
        Assert-ExpectedGitSha -ExpectedSha $ExpectedGitSha
        Write-Step "Deploying current local checkout for ref $GitRef (SYNC_GIT=0)"
    }
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

if ($SkipBuildEffective -and (Test-Path -LiteralPath (Join-Path $FrontendDir "dist"))) {
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

Stop-PidFileProcess -PidFile $ApiPid
Write-Step "Trying FastAPI on port $ServerPort"
Clear-PortOrFail -Port $ServerPort
Stop-PidFileProcess -PidFile $ApiPid

$startupArgs = @(
    "-m", "uvicorn",
    "server:create_app",
    "--factory",
    "--host", "0.0.0.0",
    "--port", $ServerPort.ToString(),
    "--workers", "1"
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

$previousGoatServerPort = $env:GOAT_SERVER_PORT
$previousGoatLocalPort = $env:GOAT_LOCAL_PORT
$previousGoatRuntimeRoot = $env:GOAT_RUNTIME_ROOT
$previousGoatLogDir = $env:GOAT_LOG_DIR
$previousGoatLogPath = $env:GOAT_LOG_PATH
$previousGoatDataDir = $env:GOAT_DATA_DIR
$previousOllamaBaseUrl = $env:OLLAMA_BASE_URL
try {
    $env:GOAT_SERVER_PORT = $ServerPort.ToString()
    $env:GOAT_LOCAL_PORT = $ServerPort.ToString()
    $env:GOAT_RUNTIME_ROOT = $RuntimeRoot
    $env:GOAT_LOG_DIR = $LogsDir
    $env:GOAT_LOG_PATH = $LogDbPath
    $env:GOAT_DATA_DIR = $DataDir
    $env:OLLAMA_BASE_URL = $ResolvedOllamaBaseUrl
    $process = Start-Process @startInfo
} finally {
    $env:GOAT_SERVER_PORT = $previousGoatServerPort
    $env:GOAT_LOCAL_PORT = $previousGoatLocalPort
    $env:GOAT_RUNTIME_ROOT = $previousGoatRuntimeRoot
    $env:GOAT_LOG_DIR = $previousGoatLogDir
    $env:GOAT_LOG_PATH = $previousGoatLogPath
    $env:GOAT_DATA_DIR = $previousGoatDataDir
    $env:OLLAMA_BASE_URL = $previousOllamaBaseUrl
}

Set-Content -LiteralPath $ApiPid -Value $process.Id -Encoding utf8

if (-not (Test-DeploymentContract -Port $ServerPort)) {
    Stop-PidFileProcess -PidFile $ApiPid
    throw "FastAPI did not become healthy on port $ServerPort."
}

Write-Step "Running post-deploy contract checks"
Push-Location -LiteralPath $ProjectDir
try {
    $env:GOAT_RUNTIME_ROOT = $RuntimeRoot
    $env:GOAT_LOG_DIR = $LogsDir
    $env:GOAT_LOG_PATH = $LogDbPath
    $env:GOAT_DATA_DIR = $DataDir
    & $VenvPython -m tools.ops.post_deploy_check --base-url "http://127.0.0.1:$ServerPort"
} finally {
    Pop-Location
    $env:GOAT_RUNTIME_ROOT = $previousGoatRuntimeRoot
    $env:GOAT_LOG_DIR = $previousGoatLogDir
    $env:GOAT_LOG_PATH = $previousGoatLogPath
    $env:GOAT_DATA_DIR = $previousGoatDataDir
}
if ($LASTEXITCODE -ne 0) {
    Stop-PidFileProcess -PidFile $ApiPid
    throw "Post-deploy contract checks failed on port $ServerPort."
}

$stopPidText = if (Test-Path -LiteralPath $ApiPid) {
    (Get-Content -LiteralPath $ApiPid -ErrorAction SilentlyContinue | Select-Object -First 1)
} else {
    "<missing pid file>"
}

Write-Host ""
Write-Host "GOAT AI deployment complete"
Write-Host "API health: http://127.0.0.1:$ServerPort/api/health"
Write-Host "API contract: http://127.0.0.1:$ServerPort/api/models/capabilities?model=gemma4:26b"
Write-Host "OLLAMA_BASE_URL: $ResolvedOllamaBaseUrl"
Write-Host "FastAPI log: $ApiLog"
Write-Host "FastAPI err: $ApiErrLog"
Write-Host "Stop command: Stop-Process -Id $stopPidText"
