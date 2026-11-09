from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_dashboard_page():
    response = client.get("/dashboard")

    assert response.status_code == 200
    assert "AI Infrastructure Copilot" in response.text
    assert 'id="cpu-value"' in response.text
    assert 'id="memory-value"' in response.text
    assert 'id="disk-value"' in response.text
    assert 'id="history-body"' in response.text
    assert 'id="history-limit"' in response.text
    assert 'id="history-chart"' in response.text
    assert 'id="incidents-list"' in response.text
    assert 'id="incident-detail-content"' in response.text
    assert 'id="diagnosis-form"' in response.text
    assert 'id="confirm-external-send"' in response.text


def test_dashboard_static_assets():
    css_response = client.get(
        "/dashboard/static/dashboard.css"
    )
    javascript_response = client.get(
        "/dashboard/static/dashboard.js"
    )
    chart_response = client.get(
        "/dashboard/static/dashboard-chart.js"
    )
    operations_response = client.get(
        "/dashboard/static/dashboard-operations.js"
    )

    assert css_response.status_code == 200
    assert "text/css" in css_response.headers[
        "content-type"
    ]

    assert javascript_response.status_code == 200
    assert "javascript" in javascript_response.headers[
        "content-type"
    ]

    assert chart_response.status_code == 200
    assert "javascript" in chart_response.headers[
        "content-type"
    ]

    assert operations_response.status_code == 200
    assert "javascript" in operations_response.headers[
        "content-type"
    ]
