#!/usr/bin/env python3
"""
EV Charging Station PSO Optimizer - Main Entrypoint & Demo Runner
"""
import sys
import argparse
from pathlib import Path

# Add backend directory to sys.path
BASE_DIR = Path(__file__).resolve().parent
BACKEND_DIR = BASE_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.data.city_data import get_scenario_data
from app.models.schemas import PSOConfig
from app.algorithm.pso import PSOLocationOptimizer
from app.algorithm.baseline import BaselineRandomOptimizer, compute_comparison_metrics


def run_demo(scenario_id: str = "austin_metro", k: int = 6, swarm_size: int = 30, iterations: int = 50, radius: float = 3.5):
    print("=" * 70)
    print("   EV CHARGING STATION OPTIMIZATION - PARTICLE SWARM (PSO)   ")
    print("=" * 70)
    print(f"Scenario:           {scenario_id}")
    print(f"Target Stations:    {k}")
    print(f"Service Radius:     {radius} km")
    print(f"Swarm Size:         {swarm_size} particles")
    print(f"Max Iterations:     {iterations}")
    print("-" * 70)

    scenario = get_scenario_data(scenario_id)
    boundary = scenario["city_boundary"]
    demands = scenario["demand_points"]
    grid_nodes = scenario["power_grid_nodes"]

    cfg = PSOConfig(
        scenario_id=scenario_id,
        k_stations=k,
        service_radius_km=radius,
        swarm_size=swarm_size,
        max_iterations=iterations,
    )

    print("\n[1/2] Executing Particle Swarm Optimization (PSO)...")
    pso = PSOLocationOptimizer(cfg, boundary, demands, grid_nodes)
    pso_res = pso.optimize()

    print(f"  + Completed in:       {pso_res.computation_time_ms:.1f} ms")
    print(f"  + Demand Coverage:    {pso_res.coverage_pct:.1f}%")
    print(f"  + Average EV Distance:{pso_res.avg_distance_km:.2f} km")
    print(f"  + Estimated Cost:     ${pso_res.total_cost:,.2f}")
    print(f"  + Multi-Obj Fitness:  {pso_res.fitness:.5f}")

    print("\n[Optimal Station Locations Placed by PSO]:")
    for s in pso_res.stations:
        print(f"  * {s.id}: Lat {s.lat:8.4f}, Lng {s.lng:9.4f} | Covers {s.covered_demand_count:2d} zones | EV Weight: {s.served_total_weight:6.1f} | Cost: ${s.installation_cost:,.2f}")

    print("\n[2/2] Comparing Against Baseline (Random Placement)...")
    base = BaselineRandomOptimizer(cfg, boundary, demands, grid_nodes)
    base_res = base.run()
    comp = compute_comparison_metrics(pso_res, base_res)

    print("-" * 70)
    print(f"Metric                  | Random Baseline  | PSO Optimized   | Improvement")
    print("-" * 70)
    print(f"Coverage                | {base_res.coverage_pct:6.1f}%          | {pso_res.coverage_pct:6.1f}%         | {comp.coverage_gain_pct:+6.1f}%")
    print(f"Avg Travel Distance     | {base_res.avg_distance_km:6.2f} km        | {pso_res.avg_distance_km:6.2f} km       | {comp.distance_reduction_pct:+6.1f}%")
    print(f"Total Capital Cost      | ${base_res.total_cost:11,.2f} | ${pso_res.total_cost:11,.2f}| {comp.cost_delta_pct:+6.1f}%")
    print(f"Objective Fitness       | {base_res.fitness:8.5f}        | {pso_res.fitness:8.5f}       | {comp.fitness_improvement_pct:+6.1f}%")
    print("-" * 70)
    print(f"Summary: {comp.summary}\n")


def start_server(host: str = "127.0.0.1", port: int = 8000):
    print(f"Starting FastAPI server on http://{host}:{port} ...")
    print(f"Swagger API Docs: http://{host}:{port}/docs")
    import uvicorn
    uvicorn.run("app.main:app", host=host, port=port, reload=True, app_dir=str(BACKEND_DIR))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="EV Charging Station PSO Optimizer Runner")
    parser.add_argument("--serve", action="store_true", help="Start FastAPI backend server")
    parser.add_argument("--scenario", type=str, default="austin_metro", choices=["austin_metro", "san_francisco_bay"], help="City scenario")
    parser.add_argument("-k", "--stations", type=int, default=6, help="Number of charging stations to place")
    parser.add_argument("-r", "--radius", type=float, default=3.5, help="Coverage radius in km")
    parser.add_argument("-p", "--particles", type=int, default=30, help="PSO swarm size")
    parser.add_argument("-i", "--iterations", type=int, default=50, help="PSO max iterations")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Server host")
    parser.add_argument("--port", type=int, default=8000, help="Server port")

    args = parser.parse_args()

    if args.serve:
        start_server(host=args.host, port=args.port)
    else:
        run_demo(
            scenario_id=args.scenario,
            k=args.stations,
            swarm_size=args.particles,
            iterations=args.iterations,
            radius=args.radius
        )

