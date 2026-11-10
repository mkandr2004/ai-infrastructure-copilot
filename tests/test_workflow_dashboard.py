from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_dashboard_contains_workflow_interface():
    response = client.get("/dashboard")

    assert response.status_code == 200
    assert 'id="workflow-form"' in response.text
    assert 'id="workflows-list"' in response.text
    assert 'id="workflow-result"' in response.text
    assert 'id="workflow-result-steps"' in response.text
    assert 'id="workflow-result-findings"' in response.text
    assert 'id="workflow-confirm-external-send"' in response.text


def test_dashboard_serves_workflow_javascript():
    response = client.get(
        "/dashboard/static/dashboard-workflows.js"
    )

    assert response.status_code == 200
    assert "javascript" in response.headers["content-type"]
    assert "loadWorkflows" in response.text
    assert 'fetch("/workflows"' in response.text
