#!/bin/bash

# Activate .venv
source .venv/bin/activate

# Kill any existing uvicorn processes on port 8001
pkill -f "uvicorn src.main:app"

# Run the app with additional watch directories for neo-commons
# This will watch both the local src directory and the neo-commons library
uvicorn src.main:app --reload --port 8001 --reload-dir src --reload-dir ../neo-commons/src