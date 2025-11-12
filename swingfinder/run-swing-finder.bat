@echo off
REM === Activate local virtual environment ===
cd /d "%~dp0"
call .venv\Scripts\activate

REM === Launch Streamlit with local Python interpreter ===
python -m streamlit run app.py

REM === Keep window open after exit ===
pause


