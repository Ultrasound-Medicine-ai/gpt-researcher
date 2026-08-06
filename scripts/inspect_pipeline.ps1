# Inspect research pipeline: search volume, context size, chat traces
#
# After a UI research run:
#   .\scripts\inspect_pipeline.ps1
#
# While researching in UI (live refresh):
#   .\scripts\inspect_pipeline.ps1 -Watch
#
# Run one research job with full metrics (no UI):
#   .\scripts\inspect_pipeline.ps1 -Live -Query "What is CRISPR?"

[CmdletBinding()]
param(
    [switch]$Live,
    [switch]$Watch,
    [string]$Query = "What is CRISPR and one application?",
    [string]$CondaEnv = "gptresearcher"
)

$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

function Get-TracePython {
    param([string]$EnvName)
    $candidates = @(
        "D:\anaconda3\envs\$EnvName\python.exe"
        "$env:USERPROFILE\anaconda3\envs\$EnvName\python.exe"
        "$env:USERPROFILE\miniconda3\envs\$EnvName\python.exe"
    )
    foreach ($c in $candidates) {
        if (Test-Path $c) { return $c }
    }
    return (Get-Command python -ErrorAction SilentlyContinue).Source
}

$Python = Get-TracePython -EnvName $CondaEnv
if (-not $Python) {
    Write-Error "Python not found. Run: conda activate $CondaEnv"
    exit 1
}

$script = Join-Path $RepoRoot "scripts\inspect_pipeline.py"
$argsList = @($script)

if ($Live) {
    $argsList += @("--mode", "live", "--query", $Query)
} elseif ($Watch) {
    $argsList += @("--mode", "watch")
} else {
    $argsList += @("--mode", "summary")
}

& $Python @argsList
exit $LASTEXITCODE
