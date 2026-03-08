import uvicorn
import sys
import logging
from config import HOST, PORT

# Configure logging (basic setup, uvicorn will add its own)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ColorDaysLogger")

def main():
    """Main function to run the FastAPI server."""
    print(f"Starting ColorDays server on {HOST}:{PORT} using FastAPI/Uvicorn...")

    # Run Uvicorn
    # reload=True is useful for dev, but maybe not prod. Defaults to False usually.
    # Given this is a dev environment conversation, reload=True is nice.
    try:
        uvicorn.run("main:app", host=HOST, port=PORT, reload=True, log_level="info")
    except KeyboardInterrupt:
        print("\nServer stopped.")

if __name__ == "__main__":
    main()