#!/bin/bash

# Check if Python is installed
if command -v python3 &> /dev/null
then
    echo "Python 3 is already installed."
else
    echo "Python 3 is not installed. Attempting to install..."

    # Install Python 3 (platform-specific)
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Debian/Ubuntu
        sudo apt-get update
        sudo apt-get install -y python3 python3-pip
    elif [[ "$OSTYPE" == "darwin"* ]]; then # macOS
        ./python-3.13.3-macos11.pkg
        fi
    else
        echo "Unsupported operating system. Please install Python 3 manually."
        exit 1
    fi

    echo "Python 3 installed successfully."
fi

# Verify Python installation
python3 --version
pip3 --version

echo "Setup complete."
../start.sh