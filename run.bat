@echo off
cd /d "%~dp0"

:: Check for Administrative Privileges
net session >nul 2>&1
if %errorLevel% == 0 (
    echo Administrative privileges confirmed.
    goto :run_app
) else (
    echo Requesting Administrator privileges...
    powershell -Command "Start-Process '%~dpnx0' -Verb RunAs"
    exit /b
)

:run_app
:: OPTIMIZATION: Set Process Priority to HIGH
:: This encourages Windows Scheduler to put Python on P-Cores
echo Setting Process Priority to HIGH...
wmic process where processid=%PROCESSID% CALL setpriority "high priority"

call venv\Scripts\activate.bat
python main.py
pause
