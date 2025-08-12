#! /bin/bash

# Kill any existing processes on port 8001
kill $(lsof -t -i:8001)

# Activate the virtual environment
source .venv/bin/activate

# Run the development server with Uvicorn
uvicorn src.main:app --reload --host 0.0.0.0 --port 8001