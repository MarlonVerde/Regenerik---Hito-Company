def test_liveness_is_independent_of_database_readiness(client, monkeypatch):
    def database_unavailable():
        raise RuntimeError("database configuration unavailable")

    monkeypatch.setattr("main.get_engine", database_unavailable)

    live = client.get("/health")
    ready = client.get("/health/ready")

    assert live.status_code == 200
    assert live.json() == {"status": "alive"}
    assert ready.status_code == 503
    assert ready.json()["detail"] == "Database unavailable"


def test_cors_allows_configured_local_frontends_and_rejects_other_origins(client):
    allowed = client.options(
        "/auth/me",
        headers={
            "Origin": "http://localhost:8080",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization",
        },
    )
    rejected = client.options(
        "/auth/me",
        headers={
            "Origin": "https://untrusted.example",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert allowed.headers["access-control-allow-origin"] == "http://localhost:8080"
    assert allowed.headers.get("access-control-allow-credentials") is None
    assert rejected.status_code == 400
