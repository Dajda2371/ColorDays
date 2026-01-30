#!/bin/bash
# Get the absolute path of the repository root
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Check if python is available, otherwise try python3
if command -v python &> /dev/null; then
    PYTHON_CMD=python
elif command -v python3 &> /dev/null; then
    PYTHON_CMD=python3
else
    echo "Error: Python is not installed."
    exit 1
fi

echo "Setting up admin password..."
"$PYTHON_CMD" "$REPO_ROOT/backend/setup_admin.py" "$@"
