def test_list_users_admin(admin_client):
    response = admin_client.get("/api/users")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_list_users_unauthorized(client):
    response = client.get("/api/users")
    assert response.status_code == 401

def test_add_user(admin_client):
    response = admin_client.post("/api/users", json={"username": "newuser"})
    assert response.status_code == 200

    response = admin_client.get("/api/users")
    users = response.json()
    assert any(u['username'] == 'newuser' for u in users)

def test_remove_user(admin_client):
    admin_client.post("/api/users", json={"username": "toremove"})
    response = admin_client.post("/api/users/remove", json={"username": "toremove"})
    assert response.status_code == 200
