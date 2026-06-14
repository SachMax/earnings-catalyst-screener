import subprocess
import sys
import os

app_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(app_dir)
os.chdir(project_root)

skip_files = {
    "build_targets.py",
    "config.py",
    'daily_update_features.py',
    'evaluation_features.py',
    'features_library.py',
    "init_features_table.py",   # run once manually
    "fetch_multiple_stocks.py", # run separately
    "fetch_price_history.py",   # run separately
    "fetch_data_intro.py",      # run separately
    "run_all_features.py",      # don't run itself
    "__init__.py",              # if any
    'historical_earnings_date.py', 
    'historical_feature.py',
    'reset_ml_dataset.py', 
    'testing.py', 
    'train_model.py'
}

all_files = [f for f in os.listdir(app_dir) if f.endswith('.py')]

all_files.sort()

for script in all_files:
    # Skip excluded files
    if script in skip_files:
        print(f"Skipping {script}")
        continue

    script_path = os.path.join("app", script) 

    print(f"\n{'='*60}")
    print(f"Running {script_path}...")
    print('='*60)
    try:
        subprocess.run([sys.executable, script_path], check=True)
        print(f"{script} completed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"{script} failed with exit code {e.returncode}. Continuing...")
    except Exception as e:
        print(f"Unexpected error running {script}: {e}")

print("\nAll feature scripts have been processed.")