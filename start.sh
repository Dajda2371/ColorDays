#!/bin/bash

cd backend

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

PYTHON_CMD="python3"
if ! command -v $PYTHON_CMD &> /dev/null; then
    PYTHON_CMD="python"
fi
PORT=$($PYTHON_CMD -c "import config; print(config.PORT)")
uvicorn main:app --host 0.0.0.0 --port $PORT --reload