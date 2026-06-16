@echo off
cd C:\Users\Sachio\OneDrive\Desktop\earnings-catalyst-screener

for /f "tokens=2-4 delims=/ " %%a in ('date /t') do set TODAY_FILE=last_sunday_%%c-%%a-%%b.txt

if exist "%TODAY_FILE%" exit /b

ping -n 1 8.8.8.8 >nul
if errorlevel 1 exit /b

C:\Users\Sachio\AppData\Local\Programs\Python\Python313\python.exe app\run_all_features.py

echo done > "%TODAY_FILE%"
echo %date% %time% Weekly feature population completed >> run_log.txt