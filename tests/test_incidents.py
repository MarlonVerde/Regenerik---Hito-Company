CSV = ("incident_id,date,location_id,category,description,status,customer_id,satisfaction_score,reporter_id\n"
    "BRS-000001,2026-01-01,COL-01,CUSTOMER_COMPLAINT,Valid complaint,CLOSED,CLI-000001,5,MGR-01\n"
    "BRS-000002,2026-01-02,COL-02,EQUIPMENT,Equipment issue,OPEN,CLI-000002,,MGR-02\n")


def test_incident_analysis_requires_auth(client):
    response = client.post("/api/incidents/analyze", files={"file": ("incidents.csv", CSV, "text/csv")})
    assert response.status_code == 401


def test_incident_analysis_happy_path_and_latest_export(client, auth_headers):
    headers, _ = auth_headers
    response = client.post("/api/incidents/analyze", headers=headers, files={"file": ("incidents.csv", CSV, "text/csv")})
    assert response.status_code == 200
    assert response.json()["source_file"] == "incidents.csv"

    latest = client.get("/api/incidents/results/latest", headers=headers)
    assert latest.status_code == 200
    exported = client.get("/api/incidents/results/export", headers=headers)
    assert exported.status_code == 200
    assert "text/csv" in exported.headers["content-type"]


def test_incident_analysis_rejects_bad_extension_and_empty_file(client, auth_headers):
    headers, _ = auth_headers
    wrong_extension = client.post("/api/incidents/analyze", headers=headers, files={"file": ("incidents.txt", CSV, "text/plain")})
    assert wrong_extension.status_code == 415
    empty = client.post("/api/incidents/analyze", headers=headers, files={"file": ("empty.csv", "", "text/csv")})
    assert empty.status_code == 400
