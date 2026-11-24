@echo off
setlocal

REM This file belongs in: <project root>\automation_scripts\run_quarterly.bat
for %%I in ("%~dp0..") do set "ROOT=%%~fI"
cd /d "%ROOT%" || exit /b 1

set "PYTHON=%ROOT%\.venv\Scripts\python.exe"
set "PYTHONPATH=%ROOT%\app;%ROOT%;%PYTHONPATH%"
set "LOGDIR=%ROOT%\runtime\run_log"
set "STATUSDIR=%ROOT%\runtime\log_status"

if not exist "%PYTHON%" (
    echo ERROR: Python not found: "%PYTHON%"
    exit /b 1
)
if not exist "%LOGDIR%" mkdir "%LOGDIR%"
if not exist "%STATUSDIR%" mkdir "%STATUSDIR%"

for /f %%D in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd"') do set "TODAY=%%D"
if not defined TODAY (
    echo ERROR: Could not determine today's date.
    exit /b 1
)

set "LOG=%LOGDIR%\quarterly_%TODAY%.log"
set "MARKER=%STATUSDIR%\quarterly_%TODAY%.done"

if exist "%MARKER%" (
    echo [%date% %time%] Already completed today.>>"%LOG%"
    echo Quarterly pipeline already completed on %TODAY%.
    exit /b 0
)

echo [%date% %time%] QUARTERLY RUN STARTED>>"%LOG%"
echo Quarterly pipeline started. Log: "%LOG%"

call :stage "app\data_pipeline\update_price_history.py" --full-refresh || goto :failed
call :stage "app\data_pipeline\historical_earnings_date.py" || goto :failed

echo Completed on %date% at %time%>"%MARKER%"
echo [%date% %time%] QUARTERLY RUN SUCCESS>>"%LOG%"
echo SUCCESS: Quarterly pipeline completed.
exit /b 0

:stage
echo Running %~1
echo [%date% %time%] START %~1>>"%LOG%"
"%PYTHON%" -u "%ROOT%\%~1" >>"%LOG%" 2>&1
if errorlevel 1 (
    echo [%date% %time%] FAILED %~1>>"%LOG%"
    echo ERROR: %~1 failed. See "%LOG%".
    exit /b 1
)
echo [%date% %time%] FINISH %~1>>"%LOG%"
exit /b 0

:failed
echo [%date% %time%] QUARTERLY RUN FAILED - no success marker created>>"%LOG%"
echo FAILED: Quarterly pipeline stopped. It can be retried today.
exit /b 1
