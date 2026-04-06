param(
    [Parameter(Mandatory = $true)]
    [string]$RepoId
)

Write-Host "Checking Hugging Face login..." -ForegroundColor Cyan
hf auth whoami
if ($LASTEXITCODE -ne 0) {
    Write-Host "You are not logged in. Run 'hf auth login' first." -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "Running submission checks..." -ForegroundColor Cyan
pytest -q
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

openenv validate .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Pushing to $RepoId ..." -ForegroundColor Cyan
openenv push . --repo-id $RepoId
exit $LASTEXITCODE
