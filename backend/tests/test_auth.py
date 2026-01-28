from config import SESSION_COOKIE_NAME
from utils import hash_password
from data_manager import user_password_store

def test_login_success(client):
    # Setup user
    password = "password123"
    hashed = hash_password(password)
    user_password_store['testuser'] = {'password_hash': hashed, 'role': 'teacher'}

    response = client.post("/login", json={"username": "testuser", "password": password})
    assert response.status_code == 200
    assert response.json()["success"] is True
    assert response.cookies.get(SESSION_COOKIE_NAME) is not None

def test_login_failure(client):
    response = client.post("/login", json={"username": "wrong", "password": "wrong"})
    assert response.status_code == 401

def test_logout(admin_client):
    response = admin_client.post("/logout")
    assert response.status_code == 200
    # Cookie should be cleared
    # Note: TestClient cookies handling for cleared cookies might depend on implementation,
    # but the response headers should contain Set-Cookie with expiry.
    # We can check headers directly if needed.
    assert "set-cookie" in response.headers
