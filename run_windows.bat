@echo off
cd /d "%~dp0"
if not exist venv\Scripts\python.exe (
  py -m venv venv
  call venv\Scripts\activate
  pip install -r requirements.txt
) else (
  call venv\Scripts\activate
)
uvicorn app.main:app --reload
