#!/bin/bash

# Activate .venv
source .venv/bin/activate

# Kill any existing uvicorn processes on port 8001
pkill -f "uvicorn src.main:app"

# Run the app
uvicorn src.main:app --reload --port 8001