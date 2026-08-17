import pytest
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)



def valid_request() -> dict:
    return {
        "goal": "学习 LangGraph",
        "current_level": "了解 Python 和 FastAPI",
        "duration_weeks": 4,
        "minutes_per_day": 90,
    }


def test_home():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "message": "StudyPilot is running"
    }


def test_create_plan():
    response = client.post(
        "/plans",
        json=valid_request(),
    )

    assert response.status_code == 201, response.text

    data = response.json()

    assert data["id"] == 1
    assert data["goal"] == "学习 LangGraph"
    assert data["duration_weeks"] == 4
    assert len(data["weekly_objectives"]) == 4
    assert len(data["tasks"]) == 4
    assert data["tasks"][0]["completed"] is False


def test_create_two_plans_with_different_ids():
    first_response = client.post(
        "/plans",
        json=valid_request(),
    )
    second_response = client.post(
        "/plans",
        json=valid_request(),
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 201

    assert first_response.json()["id"] == 1
    assert second_response.json()["id"] == 2


def test_list_plans():
    client.post("/plans", json=valid_request())

    response = client.get("/plans")

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_get_plan():
    create_response = client.post(
        "/plans",
        json=valid_request(),
    )
    plan_id = create_response.json()["id"]

    response = client.get(f"/plans/{plan_id}")

    assert response.status_code == 200
    assert response.json()["id"] == plan_id


def test_get_nonexistent_plan():
    response = client.get("/plans/999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Plan not found"


def test_complete_task():
    create_response = client.post(
        "/plans",
        json=valid_request(),
    )
    plan_id = create_response.json()["id"]

    response = client.patch(
        f"/plans/{plan_id}/tasks/1",
        json={"completed": True},
    )

    assert response.status_code == 200
    assert response.json()["completed"] is True

    plan_response = client.get(f"/plans/{plan_id}")
    assert (
        plan_response.json()["tasks"][0]["completed"]
        is True
    )


def test_update_nonexistent_task():
    client.post("/plans", json=valid_request())

    response = client.patch(
        "/plans/1/tasks/999",
        json={"completed": True},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"


def test_reject_invalid_minutes():
    request_data = valid_request()
    request_data["minutes_per_day"] = 5

    response = client.post(
        "/plans",
        json=request_data,
    )

    assert response.status_code == 422


def test_reject_invalid_duration():
    request_data = valid_request()
    request_data["duration_weeks"] = 0

    response = client.post(
        "/plans",
        json=request_data,
    )

    assert response.status_code == 422