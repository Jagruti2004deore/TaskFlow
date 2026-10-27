
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Give each test its own temporary database."""
    test_db = tmp_path / "test_tasks.db"
    monkeypatch.setattr("database.DATABASE_NAME", str(test_db))

    from api import app

    with TestClient(app) as test_client:
        yield test_client


def create_user_and_get_headers(client, username="testuser",
                                email="testuser@example.com"):
    """Register a test user, log in, and return authentication headers."""
    response = client.post(
        "/auth/register",
        json={
            "username": username,
            "email": email,
            "password": "SecurePass123!",
        },
    )
    assert response.status_code == 201

    response = client.post(
        "/auth/login",
        json={
            "email": email,
            "password": "SecurePass123!",
        },
    )
    assert response.status_code == 200

    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_home(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "running"


def test_create_task(client):
    headers = create_user_and_get_headers(client)
    response = client.post(
        "/tasks",
        json={"title": "Automated test task"},
        headers=headers,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Automated test task"
    assert data["status"] == "To Do"
    assert isinstance(data["id"], int)


def test_list_tasks(client):
    headers = create_user_and_get_headers(client)
    client.post("/tasks", json={"title": "Task A"}, headers=headers)
    client.post("/tasks", json={"title": "Task B"}, headers=headers)

    response = client.get("/tasks", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_update_task(client):
    headers = create_user_and_get_headers(client)
    created = client.post(
        "/tasks",
        json={"title": "Task to update"},
        headers=headers,
    )
    task_id = created.json()["id"]

    response = client.patch(
        f"/tasks/{task_id}",
        json={"status": "In Progress"},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "In Progress"


def test_delete_task(client):
    headers = create_user_and_get_headers(client)
    created = client.post(
        "/tasks",
        json={"title": "Task to delete"},
        headers=headers,
    )
    task_id = created.json()["id"]

    response = client.delete(f"/tasks/{task_id}", headers=headers)
    assert response.status_code == 200

    tasks = client.get("/tasks", headers=headers).json()
    assert all(task["id"] != task_id for task in tasks)


def test_update_missing_task(client):
    headers = create_user_and_get_headers(client)
    response = client.patch(
        "/tasks/99999",
        json={"status": "Done"},
        headers=headers,
    )
    assert response.status_code == 404


def test_delete_missing_task(client):
    headers = create_user_and_get_headers(client)
    response = client.delete("/tasks/99999", headers=headers)
    assert response.status_code == 404


def test_reject_empty_title(client):
    headers = create_user_and_get_headers(client)
    response = client.post(
        "/tasks",
        json={"title": "   "},
        headers=headers,
    )
    assert response.status_code == 422


def test_search_tasks(client):
    headers = create_user_and_get_headers(client)
    client.post(
        "/tasks",
        json={"title": "Prepare meeting notes"},
        headers=headers,
    )
    client.post("/tasks", json={"title": "Build API"}, headers=headers)

    response = client.get("/tasks?search=meeting", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["title"] == "Prepare meeting notes"


def test_filter_and_search_tasks(client):
    headers = create_user_and_get_headers(client)
    client.post("/tasks", json={"title": "Build API"}, headers=headers)
    created = client.post(
        "/tasks",
        json={"title": "Test API"},
        headers=headers,
    )
    task_id = created.json()["id"]

    client.patch(
        f"/tasks/{task_id}",
        json={"status": "Done"},
        headers=headers,
    )

    response = client.get(
        "/tasks?status=Done&search=API",
        headers=headers,
    )
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["title"] == "Test API"


def test_paginate_tasks(client):
    headers = create_user_and_get_headers(client)

    for number in range(1, 5):
        client.post(
            "/tasks",
            json={"title": f"Task {number}"},
            headers=headers,
        )

    response = client.get(
        "/tasks?limit=2&offset=1",
        headers=headers,
    )
    assert response.status_code == 200
    tasks = response.json()
    assert len(tasks) == 2
    assert tasks[0]["title"] == "Task 2"
    assert tasks[1]["title"] == "Task 3"


def test_reject_invalid_pagination(client):
    headers = create_user_and_get_headers(client)

    response = client.get("/tasks?limit=0", headers=headers)
    assert response.status_code == 422

    response = client.get("/tasks?offset=-1", headers=headers)
    assert response.status_code == 422


def test_register_user(client):
    response = client.post(
        "/auth/register",
        json={
            "username": "testuser",
            "email": "testuser@example.com",
            "password": "SecurePass123!",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "testuser"
    assert data["email"] == "testuser@example.com"
    assert "password" not in data
    assert "hashed_password" not in data


def test_register_duplicate_email(client):
    payload = {
        "username": "testuser",
        "email": "duplicate@example.com",
        "password": "SecurePass123!",
    }
    first = client.post("/auth/register", json=payload)
    second = client.post(
        "/auth/register",
        json={
            "username": "anotheruser",
            "email": "duplicate@example.com",
            "password": "AnotherPass123!",
        },
    )
    assert first.status_code == 201
    assert second.status_code == 409


def test_register_rejects_short_password(client):
    response = client.post(
        "/auth/register",
        json={
            "username": "testuser",
            "email": "shortpass@example.com",
            "password": "123",
        },
    )
    assert response.status_code == 422


def test_login_success(client):
    client.post(
        "/auth/register",
        json={
            "username": "loginuser",
            "email": "loginuser@example.com",
            "password": "SecurePass123!",
        },
    )
    response = client.post(
        "/auth/login",
        json={
            "email": "loginuser@example.com",
            "password": "SecurePass123!",
        },
    )
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"


def test_login_wrong_password(client):
    client.post(
        "/auth/register",
        json={
            "username": "loginuser",
            "email": "loginuser@example.com",
            "password": "SecurePass123!",
        },
    )
    response = client.post(
        "/auth/login",
        json={
            "email": "loginuser@example.com",
            "password": "WrongPass123!",
        },
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password."


def test_login_unknown_email(client):
    response = client.post(
        "/auth/login",
        json={
            "email": "unknown@example.com",
            "password": "SecurePass123!",
        },
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password."


def test_invalid_token_is_rejected(client):
    response = client.get(
        "/tasks",
        headers={"Authorization": "Bearer invalid-token"},
    )
    assert response.status_code == 401


def test_protected_route_rejects_missing_token(client):
    response = client.get("/tasks")
    assert response.status_code == 401


def test_users_cannot_access_each_others_tasks(client):
    headers_a = create_user_and_get_headers(
        client, "userone", "userone@example.com"
    )
    headers_b = create_user_and_get_headers(
        client, "usertwo", "usertwo@example.com"
    )

    created = client.post(
        "/tasks",
        json={"title": "Private task"},
        headers=headers_a,
    )
    assert created.status_code == 201
    task_id = created.json()["id"]

    # User B cannot see User A's task.
    response = client.get("/tasks", headers=headers_b)
    assert response.status_code == 200
    assert response.json() == []

    # User B cannot update User A's task.
    response = client.patch(
        f"/tasks/{task_id}",
        json={"status": "Done"},
        headers=headers_b,
    )
    assert response.status_code == 404

    # User B cannot delete User A's task.
    response = client.delete(
        f"/tasks/{task_id}",
        headers=headers_b,
    )
    assert response.status_code == 404

    # User A's task still exists and is unchanged.
    response = client.get("/tasks", headers=headers_a)
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["title"] == "Private task"
    assert response.json()[0]["status"] == "To Do"
