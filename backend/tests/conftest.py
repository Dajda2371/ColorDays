import pytest
import sys
import os
from pathlib import Path

# Add backend to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from main import app
from data_manager import user_password_store, class_data_store, students_data_store
from config import VALID_SESSION_VALUE, SESSION_COOKIE_NAME, USERNAME_COOKIE_NAME, SQL_COOKIE_NAME, ADMIN_ROLE

@pytest.fixture
def client():
    # Setup test data
    user_password_store.clear()
    class_data_store.clear()
    students_data_store.clear()

    # Add a mock admin user
    user_password_store['admin'] = {
        'password_hash': '_NULL_',
        'role': ADMIN_ROLE
    }

    with TestClient(app) as c:
        yield c

@pytest.fixture
def admin_client(client):
    # Manually set cookies to simulate logged in admin
    client.cookies.set(SESSION_COOKIE_NAME, VALID_SESSION_VALUE)
    client.cookies.set(USERNAME_COOKIE_NAME, 'admin')
    client.cookies.set(SQL_COOKIE_NAME, 'admin')
    user_password_store['admin'] = {
        'password_hash': '_NULL_',
        'role': ADMIN_ROLE
    }
    return client
