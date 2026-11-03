# One-command reproduction for Windows PowerShell.
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
$env:PYTHONUTF8 = "1"
$env:HF_HOME = Join-Path (Get-Location) ".cache\hf"

if (-not (Test-Path .venv)) { python -m venv .venv }
$py = ".venv\Scripts\python.exe"
& $py -m pip install -q -r requirements.txt

$steps = @(
  "scripts/fetch_assets.py",
  "src/data.py --per-lang 50000",
  "src/train_tokenizers.py",
  "src/metrics.py --workers 4",
  "src/stats.py",
  "src/vocab_analysis.py",
  "src/metadata.py",
  "src/plots.py",
  "src/report_numbers.py",
  "scripts/build_readme.py",
  "scripts/build_report.py",
  "scripts/build_slides.py"
)
foreach ($s in $steps) {
  Write-Host ">> $s"
  & $py @($s -split " ")
  if ($LASTEXITCODE -ne 0) { throw "step failed: $s" }
}
& $py scripts/build_paper.py
if ($LASTEXITCODE -ne 0) { Write-Host "paper build skipped (install tectonic)" }
& $py -m pytest -q
