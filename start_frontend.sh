#!/bin/bash
cd "$(dirname "$0")"
echo "Starting Streamlit Frontend..."
python -m streamlit run streamlit_app.py
