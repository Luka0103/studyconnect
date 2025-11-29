import pytest
from backend.api import task_to_dict, group_to_dict, app

class DummyTask:
    # Mock class for Task model
    def __init__(self):
        self.id = 1
        self.title = "Test Task"
        self.deadline = None
        self.kind = "Homework"
        self.priority = "High"
        self.status = "Open"
        self.progress = 50
        self.group = None
        self.assignee = "user1"

class DummyGroup:
    # Mock class for Group model
    def __init__(self):
        self.id = 1
        self.name = "Group 1"
        self.description = "Desc"
        self.group_number = "A1"
        self.invite_link = "abc123"
        self.group_memberships = [] # Geändert von self.members

# Tests conversion of DummyTask to dictionary.
def test_task_to_dict_basic():
    task = DummyTask()
    result = task_to_dict(task)
    assert result["title"] == "Test Task"
    assert result["status"] == "Open"
    assert result["group"] is None

# Tests conversion of DummyGroup to dictionary.
def test_group_to_dict_basic():
    group = DummyGroup()
    result = group_to_dict(group)
    assert result["name"] == "Group 1"
    assert result["memberCount"] == 0

# Pytest fixture to configure and yield a Flask test client.
@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

# Tests the /api/login endpoint when required fields are missing.
def test_login_missing_fields(client):
    response = client.post("/api/login", json={})
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data

# Tests the /api/refresh endpoint when the token is missing from the request body.
def test_refresh_missing_token(client):
    response = client.post("/api/refresh", json={})
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "Missing refresh token"