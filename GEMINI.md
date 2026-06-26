# ColorDays

ColorDays is a web application for an elementary school in Štěnovice, Czech Republic. It's designed to simplify the process of counting points for a tradition where students wear specific colors on the three days before Easter.

## Architecture

The application is divided into a frontend and a backend.

*   The **backend** is a single Python script (`backend/program.py`) that acts as a web server. It serves the frontend's static files and provides a simple API for data management. It also handles user authentication (both password-based and Google OAuth). Data is stored in SQL files within the `backend/data` directory.

*   The **frontend** consists of several HTML, CSS, and JavaScript files. The main page (`frontend/index.html` and `frontend/script.js`) allows users to view and modify the point counts for each class. Other pages handle login, class selection, and configuration.

## Local Development

1.  Make sure you have Python 3 installed.
2.  Install the required Python packages:

    ```bash
    pip install --upgrade google-auth-oauthlib google-api-python-client requests
    ```

3.  Start the backend server:

    ```bash
    python backend/program.py
    ```

4.  Open your web browser and navigate to `http://localhost:8000`.