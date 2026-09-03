$ErrorActionPreference = "Stop"

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Error "Virtual environment not found. Run .\scripts\setup.ps1 first."
}

& .\.venv\Scripts\python.exe -m streamlit run app.py
