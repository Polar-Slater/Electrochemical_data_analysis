@echo off
cd /d "%~dp0"
if exist "%~dp0.venv\Scripts\python.exe" (
    "%~dp0.venv\Scripts\python.exe" electrochemical_toolbox.py
) else (
    python electrochemical_toolbox.py
)
pause
