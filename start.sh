#!/bin/bash

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

cd backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload