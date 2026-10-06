@echo off
cd /d "%~dp0"
python -m venv .venv
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m pip install --no-cache-dir -r requirements.txt
if errorlevel 1 goto failed
echo Setup complete. Double-click Open EIS Analysis.bat.
pause
exit /b 0
:failed
echo Setup failed. Keep this window open to read the error above.
pause
exit /b 1
