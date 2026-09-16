#!/bin/bash
cd "$(dirname "$0")"
echo "Starting FastAPI Backend on port 8000..."
python -m uvicorn app.main:app --reload --port 8000
