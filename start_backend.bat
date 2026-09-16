@echo off
echo Starting FastAPI Backend on port 8000...
cd /d "%~dp0"
python -m uvicorn app.main:app --reload --port 8000
pause
