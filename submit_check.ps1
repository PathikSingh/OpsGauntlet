Write-Host "Running OpsGauntlet submission checks..." -ForegroundColor Cyan

pytest -q
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

openenv validate .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python inference.py --scope all --quiet
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Submission checks passed." -ForegroundColor Green
