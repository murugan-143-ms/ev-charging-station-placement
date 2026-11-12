import sys
from pathlib import Path
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import pytest
import numpy as np
from app.models.schemas import PSOConfig, DemandPoint, CityBoundary, PowerGridNode
from app.data.city_data import get_scenario_data, AUSTIN_BOUNDARY_COORDS
from app.algorithm.pso import (
    point_in_polygon,
    repair_point_to_polygon,
    haversine_vectorized,
    PSOLocationOptimizer,
    estimate_station_cost
)
from app.algorithm.baseline import BaselineRandomOptimizer, compute_comparison_metrics


def test_point_in_polygon():
    # Austin Downtown [30.2672, -97.7431] is inside
    assert point_in_polygon(30.2672, -97.7431, AUSTIN_BOUNDARY_COORDS) is True
    # North Dallas [32.7767, -96.7970] is clearly outside Austin boundary
    assert point_in_polygon(32.7767, -96.7970, AUSTIN_BOUNDARY_COORDS) is False


def test_repair_point_to_polygon():
    center = [30.2747, -97.7404]
    outside_lat, outside_lng = 31.0000, -97.0000
    assert point_in_polygon(outside_lat, outside_lng, AUSTIN_BOUNDARY_COORDS) is False

    repaired_lat, repaired_lng = repair_point_to_polygon(outside_lat, outside_lng, AUSTIN_BOUNDARY_COORDS, center)
    assert point_in_polygon(repaired_lat, repaired_lng, AUSTIN_BOUNDARY_COORDS) is True


def test_haversine_distance():
    # Distance between same points must be 0
    lats = np.array([30.2672])
    lngs = np.array([-97.7431])
    d = haversine_vectorized(lats, lngs, lats, lngs)[0, 0]
    assert pytest.approx(d, abs=1e-4) == 0.0

    # Distance between Austin Downtown and The Domain (~15 km)
    domain_lat = np.array([30.4021])
    domain_lng = np.array([-97.7258])
    dist = haversine_vectorized(lats, lngs, domain_lat, domain_lng)[0, 0]
    assert 13.0 < dist < 17.0


def test_pso_guarantees_exactly_k_stations_and_boundary_containment():
    scenario = get_scenario_data("austin_metro")
    k = 5
    config = PSOConfig(
        k_stations=k,
        service_radius_km=3.5,
        swarm_size=15,
        max_iterations=15,
        seed=42
    )
    optimizer = PSOLocationOptimizer(
        config=config,
        city_boundary=scenario["city_boundary"],
        demand_points=scenario["demand_points"],
        grid_nodes=scenario["power_grid_nodes"]
    )
    result = optimizer.optimize()

    # Exact K stations returned
    assert len(result.stations) == k

    # Every single station must be inside the city boundary
    for st in result.stations:
        assert point_in_polygon(st.lat, st.lng, scenario["city_boundary"].polygon) is True
        assert st.installation_cost > 0

    # Convergence history must be recorded and monotonically non-increasing
    history = result.convergence_history
    assert len(history) == 16 # iteration 0 to 15
    for i in range(len(history) - 1):
        assert history[i + 1].best_fitness <= history[i].best_fitness + 1e-6


def test_pso_vs_baseline_comparison():
    scenario = get_scenario_data("austin_metro")
    config = PSOConfig(
        k_stations=6,
        service_radius_km=4.0,
        swarm_size=20,
        max_iterations=20,
        seed=100
    )
    pso = PSOLocationOptimizer(
        config=config,
        city_boundary=scenario["city_boundary"],
        demand_points=scenario["demand_points"],
        grid_nodes=scenario["power_grid_nodes"]
    ).optimize()

    baseline = BaselineRandomOptimizer(
        config=config,
        city_boundary=scenario["city_boundary"],
        demand_points=scenario["demand_points"],
        grid_nodes=scenario["power_grid_nodes"]
    ).run()

    comparison = compute_comparison_metrics(pso, baseline)

    # PSO fitness must be lower (better) than or equal to random
    assert pso.fitness <= baseline.fitness
    # PSO coverage should be competitive or higher than random
    assert pso.coverage_pct >= baseline.coverage_pct - 5.0

