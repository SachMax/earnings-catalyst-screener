@echo off
setlocal

REM This file belongs in: <project root>\automation_scripts\run_daily.bat
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

REM yyyy-MM-dd is stable across Windows regional date settings.
for /f %%D in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd"') do set "TODAY=%%D"
if not defined TODAY (
    echo ERROR: Could not determine today's date.
    exit /b 1
)

set "LOG=%LOGDIR%\daily_%TODAY%.log"
set "MARKER=%STATUSDIR%\daily_%TODAY%.done"

if exist "%MARKER%" (
    echo [%date% %time%] Already completed today.>>"%LOG%"
    echo Daily pipeline has already completed on %TODAY%.
    exit /b 0
)

echo [%date% %time%] DAILY RUN STARTED>>"%LOG%"
echo Daily pipeline started. Log: "%LOG%"

REM Keep these stages in dependency order.
call :stage "app\data_pipeline\update_price_history.py" || goto :failed
call :stage "app\data_pipeline\explore_earnings.py" || goto :failed
call :stage "app\data_pipeline\daily_update_features.py" || goto :failed
call :stage "app\deploy\run_all_features.py" || goto :failed
call :stage "app\deploy\evaluation_features.py" || goto :failed
call :stage "app\guidance\guidance_bert_output_dataset.py" || goto :failed
call :stage "app\deploy\generate_output_dataset.py" || goto :failed
call :stage "app\deploy\to_duckdc_cloud.py" || goto :failed

REM Create the success marker only after ALL stages finish successfully.
echo Completed on %date% at %time%>"%MARKER%"
echo [%date% %time%] DAILY RUN SUCCESS>>"%LOG%"
echo SUCCESS: Daily pipeline completed.
exit /b 0

:stage
echo Running %~1
echo [%date% %time%] START %~1>>"%LOG%"
"%PYTHON%" -u "%ROOT%\%~1" %~2 >>"%LOG%" 2>&1
if errorlevel 1 (
    echo [%date% %time%] FAILED %~1>>"%LOG%"
    echo ERROR: %~1 failed. See "%LOG%".
    exit /b 1
)
echo [%date% %time%] FINISH %~1>>"%LOG%"
exit /b 0

:failed
echo [%date% %time%] DAILY RUN FAILED - no success marker created>>"%LOG%"
echo FAILED: Pipeline stopped. It can be retried today.
exit /b 1
