$ErrorActionPreference = "Stop"

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Error "Virtual environment not found. Run .\scripts\setup.ps1 first."
}

& .\.venv\Scripts\python.exe -m pytest -q
& .\.venv\Scripts\python.exe -c "from src.pipeline import run_commerce_pipeline; result = run_commerce_pipeline(); print(result); assert result['status'] == 'success'"

Write-Host "PipePulse checks passed."
