from fastapi.testclient import TestClient
from main import app

def test_get_public_config():
    # Ensure config was loaded (which it should be if lifespan works or if module was loaded)
    # Since we created config.json before running tests, it should be picked up if the app reloads config.
    # However, 'main.py' loads config in lifespan.
    with TestClient(app) as client:
        response = client.get("/api/config/public")
        assert response.status_code == 200
        json_data = response.json()
        assert "smart_sorting" in json_data
        assert json_data["smart_sorting"] == "true"
