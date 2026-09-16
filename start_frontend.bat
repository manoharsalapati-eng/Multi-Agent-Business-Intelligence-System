@echo off
echo Starting Streamlit Frontend...
cd /d "%~dp0"
python -m streamlit run streamlit_app.py
pause
