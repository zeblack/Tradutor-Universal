# Start the application
Write-Host "Starting Simultaneous Translation App..."
Write-Host "Ensure your virtual environment is set up."

# Check if venv exists
if (!(Test-Path "venv")) {
    Write-Host "Virtual environment not found. Please run: python -m venv venv; .\venv\Scripts\pip install -r requirements.txt"
    exit
}

# Activate venv and run (using direct path to python to avoid scope issues)
Write-Host "Launching server..."
& .\venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload --log-level info
