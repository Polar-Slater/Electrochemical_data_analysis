@echo off
cd /d "%~dp0"
if exist "%~dp0..\.venv\Scripts\python.exe" (
    "%~dp0..\.venv\Scripts\python.exe" folder_batch_plot_gui.py
) else (
    python folder_batch_plot_gui.py
)
if errorlevel 1 pause
