@echo off
cd /d C:\Users\Sachio\Desktop\earnings-catalyst-screener

:: ------------------------------------------------------------------
:: Configuration
:: ------------------------------------------------------------------

set PYTHON=C:\Users\Sachio\Desktop\earnings-catalyst-screener\.venv\Scripts\python.exe
set LOG=run_log.txt

:: Delete yesterday's log
if exist "%LOG%" del /q "%LOG%"

echo ===============================================================>>"%LOG%"
echo [%date% %time%] Daily pipeline started>>"%LOG%"
echo ===============================================================>>"%LOG%"

:: Daily marker
set TODAY_FILE=last_daily_%date:/=_%.txt

if exist "%TODAY_FILE%" (
    echo [%date% %time%] Pipeline already ran today.>>"%LOG%"
    exit /b
)

:: Internet check
ping -n 1 8.8.8.8 >nul
if errorlevel 1 (
    echo [%date% %time%] ERROR: No internet connection.>>"%LOG%"
    exit /b
)

:: ================================================================
:: Stage 1
:: ================================================================
echo [%date% %time%] START  Stage 1 - explore_earnings.py>>"%LOG%"
%PYTHON% app\explore_earnings.py >>"%LOG%" 2>&1
if errorlevel 1 goto Stage1Error
echo [%date% %time%] FINISH Stage 1>>"%LOG%"

:: ================================================================
:: Stage 2
:: ================================================================
echo [%date% %time%] START  Stage 2 - run_all_features.py>>"%LOG%"
%PYTHON% app\run_all_features.py >>"%LOG%" 2>&1
if errorlevel 1 goto Stage2Error
echo [%date% %time%] FINISH Stage 2>>"%LOG%"

:: ================================================================
:: Stage 3
:: ================================================================
echo [%date% %time%] START  Stage 3 - evaluation_features.py>>"%LOG%"
%PYTHON% app\evaluation_features.py >>"%LOG%" 2>&1
if errorlevel 1 goto Stage3Error
echo [%date% %time%] FINISH Stage 3>>"%LOG%"

:: ================================================================
:: Stage 4
:: ================================================================
echo [%date% %time%] START  Stage 4 - daily_update_features.py>>"%LOG%"
%PYTHON% app\daily_update_features.py >>"%LOG%" 2>&1
if errorlevel 1 goto Stage4Error
echo [%date% %time%] FINISH Stage 4>>"%LOG%"

:: ================================================================
:: Stage 5
:: ================================================================
echo [%date% %time%] START  Stage 5 - guidance_bert_output_dataset.py>>"%LOG%"
%PYTHON% app\guidance_bert_output_dataset.py >>"%LOG%" 2>&1
if errorlevel 1 goto Stage5Error
echo [%date% %time%] FINISH Stage 5>>"%LOG%"

:: ================================================================
:: Stage 6
:: ================================================================
echo [%date% %time%] START  Stage 6 - generate_output_dataset.py>>"%LOG%"
%PYTHON% app\generate_output_dataset.py >>"%LOG%" 2>&1
if errorlevel 1 goto Stage6Error
echo [%date% %time%] FINISH Stage 6>>"%LOG%"

:: ================================================================
:: Stage 7
:: ================================================================
echo [%date% %time%] START  Stage 7 - to_duckdc_cloud.py>>"%LOG%"
%PYTHON% app\to_duckdc_cloud.py >>"%LOG%" 2>&1
if errorlevel 1 goto Stage7Error
echo [%date% %time%] FINISH Stage 7>>"%LOG%"

echo done > "%TODAY_FILE%"

echo [%date% %time%] SUCCESS - Full daily pipeline completed>>"%LOG%"
echo ===============================================================>>"%LOG%"

exit /b

:: ================================================================
:: Error handlers
:: ================================================================

:Stage1Error
echo [%date% %time%] ERROR in Stage 1 (explore_earnings.py)>>"%LOG%"
exit /b

:Stage2Error
echo [%date% %time%] ERROR in Stage 2 (run_all_features.py)>>"%LOG%"
exit /b

:Stage3Error
echo [%date% %time%] ERROR in Stage 3 (evaluation_features.py)>>"%LOG%"
exit /b

:Stage4Error
echo [%date% %time%] ERROR in Stage 4 (daily_update_features.py)>>"%LOG%"
exit /b

:Stage5Error
echo [%date% %time%] ERROR in Stage 5 (guidance_bert_output_dataset.py)>>"%LOG%"
exit /b

:Stage6Error
echo [%date% %time%] ERROR in Stage 6 (generate_output_dataset.py)>>"%LOG%"
exit /b

:Stage7Error
echo [%date% %time%] ERROR in Stage 7 (to_duckdc_cloud.py)>>"%LOG%"
exit /b