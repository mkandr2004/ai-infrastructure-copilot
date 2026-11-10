from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_dashboard_contains_alert_interface():
    response = client.get("/dashboard")

    assert response.status_code == 200
    assert 'id="alerts-title"' in response.text
    assert 'id="alerts-list"' in response.text
    assert 'id="refresh-alerts-button"' in response.text
    assert "dashboard-alerts.js" in response.text


def test_dashboard_serves_alert_javascript():
    response = client.get("/dashboard/static/dashboard-alerts.js")

    assert response.status_code == 200
    assert "loadAlerts" in response.text
    assert 'fetch(' in response.text
    assert '"/alerts?limit=20"' in response.text
