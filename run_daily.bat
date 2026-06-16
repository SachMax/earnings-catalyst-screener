@echo off
cd C:\Users\Sachio\OneDrive\Desktop\earnings-catalyst-screener

:: Build a region-proof date string for today (YYYY-MM-DD)
for /f "tokens=2-4 delims=/ " %%a in ('date /t') do set TODAY_FILE=last_daily_%%c-%%a-%%b.txt

:: Skip if already ran today
if exist "%TODAY_FILE%" exit /b

:: Internet check
ping -n 1 8.8.8.8 >nul
if errorlevel 1 exit /b

:: Run the daily scripts
C:\Users\Sachio\AppData\Local\Programs\Python\Python313\python.exe app\populate_features_batch.py
C:\Users\Sachio\AppData\Local\Programs\Python\Python313\python.exe app\guidance_data.py

:: Mark as completed for today
echo done > "%TODAY_FILE%"
echo %date% %time% Daily updates completed >> run_log.txt