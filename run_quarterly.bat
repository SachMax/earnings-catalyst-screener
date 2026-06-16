@echo off
cd C:\Users\Sachio\OneDrive\Desktop\earnings-catalyst-screener

:: Region-proof date string for today (YYYY-MM-DD)
for /f "tokens=2-4 delims=/ " %%a in ('date /t') do set TODAY_FILE=last_quarterly_%%c-%%a-%%b.txt

:: Since quarterly runs only 4 times a year, a daily marker is fine.
if exist "%TODAY_FILE%" exit /b

ping -n 1 8.8.8.8 >nul
if errorlevel 1 exit /b

C:\Users\Sachio\AppData\Local\Programs\Python\Python313\python.exe app\fetch_multiple_stocks.py
C:\Users\Sachio\AppData\Local\Programs\Python\Python313\python.exe app\historical_earnings_date.py

echo done > "%TODAY_FILE%"
echo %date% %time% Quarterly data refresh completed >> run_log.txt