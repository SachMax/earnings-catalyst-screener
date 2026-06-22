@echo off
cd C:\Users\Sachio\Desktop\earnings-catalyst-screener

:: Daily marker using today's date (slashes replaced with underscores)
set TODAY_FILE=last_daily_%date:/=_%.txt

:: Skip if already ran today
if exist "%TODAY_FILE%" exit /b

:: Internet check
ping -n 1 8.8.8.8 >nul
if errorlevel 1 exit /b

:: Launch all four backfill scripts in parallel
start "" C:\Users\Sachio\AppData\Local\Programs\Python\Python313\python.exe app\populate_features_batch.py
start "" C:\Users\Sachio\AppData\Local\Programs\Python\Python313\python.exe app\populate_features_batch_asc.py

:: Mark as completed for today (the scripts are still running in their own windows)
echo done > "%TODAY_FILE%"
echo %date% %time% Daily updates launched >> run_log.txt