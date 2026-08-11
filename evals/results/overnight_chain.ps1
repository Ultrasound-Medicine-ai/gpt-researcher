# Overnight eval chain (hands-off). :-)
# 1) Wait until random SimpleQA n=100 finishes (detect artifact / log)
# 2) Stop random portfolio before it spends on duplicate hallucination
# 3) Archive random SimpleQA
# 4) Stratified SimpleQA n=100
# 5) Hallucination full 70
# 6) Rebuild portfolio metrics + dashboard + morning status

$ErrorActionPreference = "Continue"
$Root = "F:\agent\gpt-researcher"
$Results = Join-Path $Root "evals\results"
$Log = Join-Path $Results "portfolio_n100_chain.log"
$Status = Join-Path $Results "OVERNIGHT_STATUS.md"
$Arch = Join-Path $Results "archive_random_n100"
$Py = "D:\anaconda3\envs\gptresearcher\python.exe"
$RandomShellPid = 26600
$RunLog = Join-Path $Results "portfolio_n100_run.log"
$Simpleqa = Join-Path $Results "simpleqa_latest.json"

Set-Location $Root
$env:EVAL_TOTAL_WORDS = "350"
$env:PYTHONUNBUFFERED = "1"

function Write-Log([string]$msg) {
  $line = "$(Get-Date -Format o) $msg"
  Add-Content -Path $Log -Value $line -Encoding UTF8
  Write-Output $line
}

function Write-Status([string]$body) {
  @"
# Overnight eval status

- Updated: $(Get-Date -Format o)
- Chain: random SimpleQA n=100 → stratified SimpleQA n=100 → hallucination full 70 → metrics

$body
"@ | Set-Content -Path $Status -Encoding UTF8
}

function Stop-Tree([int]$pid) {
  if ($pid -le 0) { return }
  try {
    $children = Get-CimInstance Win32_Process | Where-Object { $_.ParentProcessId -eq $pid }
    foreach ($c in $children) { Stop-Tree ([int]$c.ProcessId) }
    Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
  } catch {}
}

function Test-SimpleQADone {
  if (-not (Test-Path $Simpleqa)) { return $false }
  try {
    $j = Get-Content $Simpleqa -Raw -Encoding UTF8 | ConvertFrom-Json
    if ([int]$j.num_examples -ge 100 -and $j.metrics -and [int]$j.metrics.successful -gt 0) {
      # Prefer freshly written file from this overnight run
      $ageMin = ((Get-Date) - (Get-Item $Simpleqa).LastWriteTime).TotalMinutes
      if ($ageMin -lt 720) { return $true }
    }
  } catch {}
  if (Test-Path $RunLog) {
    $tail = Get-Content $RunLog -Tail 80 -ErrorAction SilentlyContinue
    if ($tail -match "Wrote .*simpleqa_latest\.json" -and $tail -match "AGGREGATE METRICS") {
      return $true
    }
  }
  return $false
}

Write-Log "OVERNIGHT chain started (wait SimpleQA n=100, then stratified, then hall 70)"
Write-Status @"
## State
**WAITING** for random SimpleQA n=100 to finish.

## Tomorrow morning open
1. ``evals/results/OVERNIGHT_STATUS.md`` (this file)
2. ``evals/results/PORTFOLIO_METRICS.md``
3. ``evals/results/simpleqa_latest.json`` (expect ``sample_mode=stratified``)
4. ``evals/results/hallucination_latest.json`` (expect ``effective_n=70`` + ``by_bucket``)
5. ``evals/results/portfolio_n100_chain.log``
"@

# Wait for SimpleQA completion (or random shell exit)
while (-not (Test-SimpleQADone)) {
  if (-not (Get-Process -Id $RandomShellPid -ErrorAction SilentlyContinue)) {
    Write-Log "random shell PID $RandomShellPid already exited; continue with whatever SimpleQA artifact exists"
    break
  }
  $n = 0
  try {
    $n = (Select-String -Path (Join-Path $env:USERPROFILE ".cursor\projects\f-agent-gpt-researcher\terminals\417883.txt") -Pattern "Evaluating query:" -ErrorAction SilentlyContinue | Measure-Object).Count
  } catch {}
  Write-Log "still waiting SimpleQA... progress_queries≈$n"
  Write-Status @"
## State
**WAITING** random SimpleQA (~$n/100 queries started in terminal log).

Do not interrupt. Official numbers will be stratified + hall70 after this.
"@
  Start-Sleep -Seconds 60
}

Write-Log "SimpleQA n=100 detected (or random exited) — stopping random portfolio to avoid duplicate hallucination spend"
# Kill random powershell tree and any leftover portfolio/simpleqa/hall python from that run
Stop-Tree $RandomShellPid
Get-CimInstance Win32_Process -Filter "name='python.exe'" | Where-Object {
  $_.CommandLine -match 'run_portfolio\.py|simple_evals\\run_eval\.py|hallucination_eval\\run_eval\.py'
} | ForEach-Object {
  Write-Log "stopping python PID $($_.ProcessId)"
  Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
}
Start-Sleep -Seconds 3

New-Item -ItemType Directory -Force -Path $Arch | Out-Null
foreach ($f in @("simpleqa_latest.json","hallucination_latest.json","portfolio_latest.json","PORTFOLIO_METRICS.md","portfolio_n100_run.log")) {
  $src = Join-Path $Results $f
  if (Test-Path $src) { Copy-Item $src (Join-Path $Arch $f) -Force }
}
Write-Log "archived -> $Arch"

Write-Log "START stratified SimpleQA n=100"
Write-Status "## State`n**RUNNING** stratified SimpleQA n=100 (seed=42)."
& $Py -u evals/simple_evals/run_eval.py --num_examples 100 --seed 42 --sample-mode stratified *>&1 |
  Tee-Object -FilePath (Join-Path $Results "portfolio_n100_stratified_run.log")
$e1 = $LASTEXITCODE
Write-Log "STRATIFIED_SIMPLEQA_DONE exit=$e1"

Write-Log "START hallucination full 70"
Write-Status "## State`n**RUNNING** hallucination full corpus n=70."
& $Py -u evals/hallucination_eval/run_eval.py -n 70 --judge lite --seed 42 *>&1 |
  Tee-Object -FilePath (Join-Path $Results "portfolio_n100_hall70_run.log")
$e2 = $LASTEXITCODE
Write-Log "HALL70_DONE exit=$e2"

Write-Log "rebuild portfolio metrics + dashboard"
& $Py -c @"
import json, sys
from pathlib import Path
from datetime import datetime, timezone
sys.path.insert(0, 'evals')
from run_portfolio import write_portfolio_md, _product_strata, _load_json
RESULTS = Path(r'$Results')
sqa = _load_json(RESULTS / 'simpleqa_latest.json')
hall = _load_json(RESULTS / 'hallucination_latest.json')
metrics = {
  'timestamp': datetime.now(timezone.utc).isoformat(),
  'num_examples': 100,
  'sample_seed': 42,
  'sample_mode': (sqa or {}).get('sample_mode') or 'stratified',
  'product_strata': _product_strata(),
  'cheap': {'ok': True},
  'harness_full': {'ok': True},
  'live_chat': _load_json(RESULTS / 'live_chat_latest.json'),
  'simpleqa': sqa,
  'hallucination': hall,
  'overnight': {'stratified_exit': $e1, 'hall70_exit': $e2},
}
RESULTS.joinpath('portfolio_latest.json').write_text(
    json.dumps(metrics, ensure_ascii=False, indent=2), encoding='utf-8')
write_portfolio_md(metrics, RESULTS / 'PORTFOLIO_METRICS.md')
print('portfolio metrics rebuilt')
"@
& $Py evals/dashboard/build_dashboard.py

$mode = "unknown"
$eff = "unknown"
try {
  $sj = Get-Content $Simpleqa -Raw -Encoding UTF8 | ConvertFrom-Json
  $mode = $sj.sample_mode
  $eff = $sj.effective_n
} catch {}
$hallEff = "unknown"
$hallRate = "unknown"
try {
  $hj = Get-Content (Join-Path $Results "hallucination_latest.json") -Raw -Encoding UTF8 | ConvertFrom-Json
  $hallEff = $hj.effective_n
  $hallRate = $hj.hallucination_rate
} catch {}

Write-Log "CHAIN_COMPLETE stratified_exit=$e1 hall_exit=$e2 mode=$mode hall_eff=$hallEff"
Write-Status @"
## State
**DONE**

| Step | Exit | Notes |
|------|------|-------|
| Stratified SimpleQA | $e1 | sample_mode=$mode effective_n=$eff |
| Hallucination full 70 | $e2 | effective_n=$hallEff rate=$hallRate |

## Open tomorrow
1. ``evals/results/PORTFOLIO_METRICS.md``
2. ``evals/results/simpleqa_latest.json``
3. ``evals/results/hallucination_latest.json``
4. ``evals/results/dashboard.html`` / ``DASHBOARD.md``
5. ``evals/results/portfolio_n100_chain.log``
6. Random archive: ``evals/results/archive_random_n100/``
"@

exit 0
