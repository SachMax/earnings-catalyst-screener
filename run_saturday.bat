@echo off
cd C:\Users\Sachio\OneDrive\Desktop\earnings-catalyst-screener

:: Region-proof date string for today (YYYY-MM-DD)
for /f "tokens=2-4 delims=/ " %%a in ('date /t') do set TODAY_FILE=last_saturday_%%c-%%a-%%b.txt

:: Skip if already ran today (prevents running twice on Saturday)
if exist "%TODAY_FILE%" exit /b

ping -n 1 8.8.8.8 >nul
if errorlevel 1 exit /b

C:\Users\Sachio\AppData\Local\Programs\Python\Python313\python.exe app\explore_earnings.py

echo done > "%TODAY_FILE%"
echo %date% %time% Earnings calendar refreshed >> run_log.txt