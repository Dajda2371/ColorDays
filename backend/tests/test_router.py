from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)
client.cookies.update({
    "ColorDaysSession": "user_is_logged_in_secret_value",
    "SQLAuthUser": "Admin"
})

response = client.get("/api/student/counting-details?code=GBvYS&day=1")
print(response.status_code)
print(response.json())
