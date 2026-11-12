from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health():
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"


def test_scenarios():
    res = client.get("/api/scenarios")
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 2
    assert any(s["id"] == "austin_metro" for s in data)


def test_scenario_data():
    res = client.get("/api/scenario-data?scenario_id=austin_metro")
    assert res.status_code == 200
    payload = res.json()
    assert "city_boundary" in payload
    assert "power_grid_nodes" in payload
    assert "demand_points" in payload
    assert len(payload["demand_points"]) == 50


def test_optimize_endpoint():
    req_body = {
        "k_stations": 4,
        "service_radius_km": 3.0,
        "swarm_size": 15,
        "max_iterations": 10,
        "scenario_id": "austin_metro"
    }
    res = client.post("/api/optimize", json=req_body)
    assert res.status_code == 200
    data = res.json()
    assert len(data["stations"]) == 4
    assert data["avg_distance_km"] > 0
    assert 0 <= data["coverage_pct"] <= 100.0


def test_compare_endpoint():
    req_body = {
        "k_stations": 4,
        "service_radius_km": 3.5,
        "swarm_size": 15,
        "max_iterations": 10,
        "scenario_id": "austin_metro"
    }
    res = client.post("/api/compare", json=req_body)
    assert res.status_code == 200
    data = res.json()
    assert "pso" in data
    assert "baseline" in data
    assert "comparison" in data
    assert len(data["pso"]["stations"]) == 4
    assert len(data["baseline"]["stations"]) == 4

