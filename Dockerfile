FROM python:3.11-slim

WORKDIR /app

# Install dependencies first for better caching
COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy the entire application (excluding items in .dockerignore)
COPY . .

# Expose port (as configured in config.py)
EXPOSE 443

# Change to the backend directory, so uvicorn starts the main module correctly
WORKDIR /app/backend

# Command to run the application (similar to start.sh)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "443"]
