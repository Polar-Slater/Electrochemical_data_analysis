@echo off
cd /d "%~dp0"
python tafel_gui.py
if errorlevel 1 pause
