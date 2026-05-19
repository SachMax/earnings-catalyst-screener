import os
from pathlib import Path

# 1. Where is Python actually looking for .env?
print("Current working directory:", Path.cwd())
print(".env file exists here:", (Path.cwd() / ".env").exists())
print(".env file exists in parent:", (Path.cwd().parent / ".env").exists())

# 2. Try to load it and see what happens
from dotenv import load_dotenv
loaded = load_dotenv(verbose=True)  # verbose=True will print extra debug info
print("load_dotenv returned:", loaded)

# 3. Try reading the key
key = os.getenv("FINNHUB_API_KEY")
if key:
    print(f"Key loaded successfully: {key[:5]}...{key[-4:]}")
else:
    print("Key is None. Checking all environment variables...")
    # Print all env vars that contain 'FINNHUB' or 'API'
    for k, v in os.environ.items():
        if 'FINNHUB' in k or 'API' in k:
            print(f"Found: {k} = {v[:10]}...")