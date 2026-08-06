# GPT Researcher smoke check
# Run after each change to verify API, UI, chat, and (optionally) full research pipeline.
#
# Quick (~30s, services must be running):
#   .\scripts\smoke_check.ps1
#
# Full pipeline + report quality (~2-10 min, uses Tavily + LLM):
#   .\scripts\smoke_check.ps1 -Full
#
# Prerequisites:
#   Terminal 1: conda activate gptresearcher; python main.py
#   Terminal 2: cd frontend/nextjs; npm run dev

[CmdletBinding()]
param(
    [switch]$Full,
    [switch]$SkipPytest,
    [switch]$SkipUi,
    [switch]$OpenReport,
    [string]$ApiUrl = "http://localhost:8000",
    [string]$UiUrl = "http://localhost:3000",
    [string]$CondaEnv = "gptresearcher",
    [int]$ResearchTimeoutSec = 600
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

$Passed = 0
$Failed = 0
$Warnings = 0

function Write-Step([string]$Message) {
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Write-Pass([string]$Message) {
    $script:Passed++
    Write-Host "  [PASS] $Message" -ForegroundColor Green
}

function Write-Fail([string]$Message) {
    $script:Failed++
    Write-Host "  [FAIL] $Message" -ForegroundColor Red
}

function Write-Warn([string]$Message) {
    $script:Warnings++
    Write-Host "  [WARN] $Message" -ForegroundColor Yellow
}

function Get-SmokePython {
    param([string]$EnvName)

    $names = @(
        "D:\anaconda3\envs\$EnvName\python.exe"
        "$env:USERPROFILE\anaconda3\envs\$EnvName\python.exe"
        "$env:USERPROFILE\miniconda3\envs\$EnvName\python.exe"
        if ($env:CONDA_DEFAULT_ENV -eq $EnvName -and $env:CONDA_PREFIX) {
            Join-Path $env:CONDA_PREFIX "python.exe"
        }
    ) | Where-Object { $_ }

    foreach ($candidate in $names) {
        if (Test-Path $candidate) {
            return $candidate
        }
    }

    $fromPath = Get-Command python -ErrorAction SilentlyContinue
    if ($fromPath) {
        return $fromPath.Source
    }

    return $null
}

function Test-PortListening {
    param([int]$Port)
    $match = netstat -ano | Select-String "LISTENING" | Select-String ":$Port\s"
    return [bool]$match
}

function Read-DotEnvValue {
    param([string]$Key)
    $envFile = Join-Path $RepoRoot ".env"
    if (-not (Test-Path $envFile)) { return $null }
    foreach ($line in Get-Content $envFile) {
        if ($line -match "^\s*$Key\s*=\s*(.+)\s*$") {
            return $Matches[1].Trim().Trim('"').Trim("'")
        }
    }
    return $null
}

Write-Host ""
Write-Host "GPT Researcher Smoke Check" -ForegroundColor White
Write-Host "Repo: $RepoRoot"
Write-Host "Mode: $(if ($Full) { 'FULL (research + quality)' } else { 'QUICK (health + chat)' })"

# --- Phase 1: Environment ---
Write-Step "Phase 1 - Environment"

$Python = Get-SmokePython -EnvName $CondaEnv
if (-not $Python) {
    Write-Fail "Python not found. Activate conda env '$CondaEnv' or install dependencies."
    exit 1
}
Write-Pass "Python: $Python"

if (-not (Test-Path (Join-Path $RepoRoot ".env"))) {
    Write-Warn ".env missing - copy from .env.example and configure API keys"
} else {
    Write-Pass ".env present"
}

$tavily = Read-DotEnvValue "TAVILY_API_KEYS"
if (-not $tavily) { $tavily = Read-DotEnvValue "TAVILY_API_KEY" }
if ($tavily) {
    Write-Pass "Tavily key configured (research + chat search enabled)"
} else {
    Write-Warn "TAVILY_API_KEY(S) not set - research/chat web search may fail"
}

$retriever = Read-DotEnvValue "RETRIEVER"
if ($retriever) {
    Write-Pass "RETRIEVER=$retriever"
} else {
    Write-Warn "RETRIEVER not set in .env (defaults to tavily in code)"
}

# --- Phase 2: Services ---
Write-Step "Phase 2 - Services (must be running)"

$apiUp = Test-PortListening -Port 8000
$uiUp = Test-PortListening -Port 3000

if ($apiUp) { Write-Pass "Port 8000 listening (API)" } else { Write-Fail "Port 8000 not listening - run: conda activate $CondaEnv; python main.py" }
if ($SkipUi) {
    Write-Warn "UI check skipped (-SkipUi)"
} elseif ($uiUp) {
    Write-Pass "Port 3000 listening (Next.js)"
} else {
    Write-Fail "Port 3000 not listening - run: cd frontend/nextjs; npm run dev"
}

if (-not $apiUp) {
    Write-Host ""
    Write-Host "Start services first, then re-run smoke check." -ForegroundColor Red
    exit 1
}

# --- Phase 3: Pytest (fast, no live API) ---
if (-not $SkipPytest) {
    Write-Step "Phase 3 - Unit tests (offline)"
    $pytestFiles = @(
        "tests/test_tavily_key_pool.py",
        "tests/test_agent_discovery.py",
        "tests/test_websocket_manager.py"
    )
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $pipShow = & $Python -m pip show pytest 2>&1 | Out-String
    $ErrorActionPreference = $prevEap
    $pytestAvailable = $pipShow -match "Name:\s*pytest"
    if (-not $pytestAvailable) {
        Write-Warn "pytest not installed in $CondaEnv - skip with -SkipPytest or: pip install pytest pytest-asyncio"
    } else {
        try {
            & $Python -m pytest @pytestFiles -q
            if ($LASTEXITCODE -eq 0) {
                Write-Pass "pytest ($($pytestFiles.Count) files)"
            } else {
                Write-Fail "pytest failed (exit $LASTEXITCODE)"
            }
        } catch {
            Write-Fail "pytest error: $_"
        }
    }
} else {
    Write-Warn "pytest skipped (-SkipPytest)"
}

# --- Phase 4: E2E (live API) ---
Write-Step "Phase 4 - Live E2E checks"

$e2eScript = Join-Path $RepoRoot "scripts\smoke_e2e.py"
$e2eMode = if ($Full) { "full" } else { "quick" }

Write-Host "  Running: python scripts/smoke_e2e.py --mode $e2eMode"

$e2eParams = @(
    $e2eScript,
    "--api-url", $ApiUrl,
    "--ui-url", $UiUrl,
    "--mode", $e2eMode
)

if ($Full) {
    $e2eParams += @("--timeout", "$ResearchTimeoutSec")
}
if ($SkipUi) {
    $e2eParams += @("--skip-ui")
}

& $Python @e2eParams
$e2eExit = $LASTEXITCODE

if ($e2eExit -eq 0) {
    Write-Pass "smoke_e2e.py"
} else {
    Write-Fail "smoke_e2e.py failed (exit $e2eExit)"
}

# --- Phase 5: Report quality artifacts (Full mode) ---
$latestSmoke = Get-ChildItem -Path (Join-Path $RepoRoot "outputs\smoke") -Directory -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

if ($Full -and $latestSmoke) {
    Write-Step "Phase 5 - Report quality review"
    $summaryPath = Join-Path $latestSmoke.FullName "summary.txt"
    $reportPath = Join-Path $latestSmoke.FullName "report.md"
    if (Test-Path $summaryPath) {
        Get-Content $summaryPath | ForEach-Object { Write-Host "  $_" }
    }
    if (Test-Path $reportPath) {
        Write-Pass "Report saved: $reportPath"
        if ($OpenReport) {
            Start-Process $reportPath
        }
    }
}

# --- Summary ---
Write-Host ""
Write-Host "========================================" -ForegroundColor White
Write-Host "  PASS: $Passed   FAIL: $Failed   WARN: $Warnings" -ForegroundColor White
Write-Host "========================================" -ForegroundColor White

if ($Failed -gt 0 -or $e2eExit -ne 0) {
    Write-Host ""
    Write-Host "Smoke check FAILED. Do not commit until fixed." -ForegroundColor Red
    Write-Host ""
    Write-Host "Typical fixes:" -ForegroundColor Yellow
    Write-Host "  1. conda activate $CondaEnv"
    Write-Host "  2. python main.py          # API :8000"
    Write-Host "  3. cd frontend/nextjs; npm run dev   # UI :3000"
    Write-Host "  4. Re-run: .\scripts\smoke_check.ps1$(if ($Full) { ' -Full' })"
    exit 1
}

Write-Host ""
Write-Host "Smoke check PASSED." -ForegroundColor Green
if (-not $Full) {
    Write-Host "Tip: run .\scripts\smoke_check.ps1 -Full -OpenReport before merging larger changes." -ForegroundColor DarkGray
}
exit 0
