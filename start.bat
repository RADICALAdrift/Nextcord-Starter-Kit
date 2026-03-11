@echo off
setlocal

cd /d "%~dp0"

if not exist ".venv" (
    python -m venv .venv
)

call .venv\Scripts\activate

python -m pip install -U pip

python -m pip install -r requirements.txt

python bot.py

pause