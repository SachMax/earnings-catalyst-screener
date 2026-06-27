@echo off
cd C:\Users\Sachio\Desktop\earnings-catalyst-screener

:: Daily marker using today's date (slashes replaced with underscores)
set TODAY_FILE=last_daily_%date:/=_%.txt

:: Skip if already ran today
if exist "%TODAY_FILE%" exit /b

:: Internet check
ping -n 1 8.8.8.8 >nul
if errorlevel 1 exit /b

:: 1. Refresh the upcoming earnings calendar
C:\Users\Sachio\AppData\Local\Programs\Python\Python311\python.exe app\explore_earnings.py

:: 2. Run full feature population (options, sector, etc.)
C:\Users\Sachio\AppData\Local\Programs\Python\Python311\python.exe app\run_all_features.py

:: 3. Rule‑based screening (Phase/Conviction)
C:\Users\Sachio\AppData\Local\Programs\Python\Python311\python.exe app\evaluation_features.py

:: 4. Refresh upcoming features in ml_dataset
C:\Users\Sachio\AppData\Local\Programs\Python\Python311\python.exe app\daily_update_features.py

:: 5. Backfill guidance probabilities for upcoming events
C:\Users\Sachio\AppData\Local\Programs\Python\Python311\python.exe app\guidance_bert_output_dataset.py

:: 6. Generate the dashboard table
C:\Users\Sachio\AppData\Local\Programs\Python\Python311\python.exe app\generate_output_dataset.py

:: 7. Update local database to MOTHERDUCK Cloud Database
C:\Users\Sachio\Desktop\earnings-catalyst-screener\app\to_duckdc_cloud.py

:: 8. Backfill historical ml_dataset rows (keeps training set growing)
C:\Users\Sachio\AppData\Local\Programs\Python\Python311\python.exe app\populate_features_batch_desc.py

:: runs everyday at 8pm 
:: Mark as completed for today (the scripts are still running in their own windows)
echo done > "%TODAY_FILE%"
echo %date% %time% Full daily pipeline completed >> run_log.txt