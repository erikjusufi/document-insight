from fastapi.testclient import TestClient

from app.main import create_app


def test_cors_preflight_allows_frontend_origin() -> None:
    app = create_app()
    client = TestClient(app)

    response = client.options(
        "/auth/login",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"
