@echo off
cd C:\Users\Sachio\Desktop\earnings-catalyst-screener

:: Simple daily marker (runs only once on the quarterly trigger day)
set TODAY_FILE=last_quarterly_%date:/=_%.txt

if exist "%TODAY_FILE%" exit /b

ping -n 1 8.8.8.8 >nul
if errorlevel 1 exit /b

C:\Users\Sachio\AppData\Local\Programs\Python\Python313\python.exe app\fetch_multiple_stocks.py
C:\Users\Sachio\AppData\Local\Programs\Python\Python313\python.exe app\historical_earnings_date.py

echo done > "%TODAY_FILE%"
echo %date% %time% Quarterly data refresh completed >> run_log.txt