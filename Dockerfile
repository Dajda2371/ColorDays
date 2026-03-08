FROM python:3.11-slim

WORKDIR /app

# Install dependencies first for better caching
COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy the entire application (excluding items in .dockerignore)
COPY . .

# Expose port (as configured in config.py) - you may need to adjust this depending on how you run the image
# EXPOSE 443

# Change to the backend directory, so uvicorn starts the main module correctly
WORKDIR /app/backend

# Command to run the application dynamically picking up the port from config.py
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port $(python -c 'import config; print(config.PORT)')"]
