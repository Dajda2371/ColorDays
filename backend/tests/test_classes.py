def test_add_class(admin_client):
    data = {
        "class": "1.A",
        "teacher": "Mr. Smith",
        "counts1": "T",
        "counts2": "T",
        "counts3": "T"
    }
    response = admin_client.post("/api/classes/add", json=data)
    assert response.status_code == 200

    response = admin_client.get("/api/classes")
    classes = response.json()
    assert any(c['class'] == "1.A" for c in classes)

def test_remove_class(admin_client):
    data = {
        "class": "1.B",
        "teacher": "Mr. Jones"
    }
    admin_client.post("/api/classes/add", json=data)

    response = admin_client.post("/api/classes/remove", json={"class": "1.B"})
    assert response.status_code == 200

    response = admin_client.get("/api/classes")
    classes = response.json()
    assert not any(c['class'] == "1.B" for c in classes)
