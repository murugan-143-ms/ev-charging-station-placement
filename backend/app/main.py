import sys
import time
from pathlib import Path
from typing import Dict, Any, List

# Ensure backend root is on sys.path so 'app' imports work from any working directory
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware

from app.models.schemas import (
    PSOConfig,
    OptimizationResult,
    ComparisonResponse,
    CityBoundary,
    DemandPoint,
    PowerGridNode
)
from app.data.city_data import get_scenario_data
from app.algorithm.pso import PSOLocationOptimizer
from app.algorithm.baseline import BaselineRandomOptimizer, compute_comparison_metrics

app = FastAPI(
    title="EV Charging Station Location Optimization API",
    description="Backend API powered by Particle Swarm Optimization (PSO) to determine optimal charging station placement.",
    version="1.0.0"
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": "EV Charging Station PSO Optimizer",
        "timestamp": time.time()
    }


@app.get("/api/scenarios")
def list_scenarios():
    return [
        {
            "id": "austin_metro",
            "name": "Austin Metropolitan Area (Texas EV Corridor)",
            "description": "High-growth tech hub featuring downtown urban core, The Domain tech cluster, Giga Texas corridor, and suburban rings.",
            "default_k": 6,
            "center": [30.2747, -97.7404],
            "demand_count": 50,
        },
        {
            "id": "san_francisco_bay",
            "name": "San Francisco Peninsula EV Grid",
            "description": "Dense coastal peninsula featuring high EV adoption rates, steep elevation constraints, and dense commercial zones.",
            "default_k": 5,
            "center": [37.7600, -122.4400],
            "demand_count": 25,
        }
    ]


@app.get("/api/scenario-data")
def get_scenario_data_endpoint(scenario_id: str = "austin_metro"):
    data = get_scenario_data(scenario_id)
    return {
        "city_boundary": data["city_boundary"],
        "power_grid_nodes": data["power_grid_nodes"],
        "demand_points": data["demand_points"],
    }


@app.post("/api/optimize", response_model=OptimizationResult)
def run_pso_optimization(config: PSOConfig = Body(...)):
    try:
        scenario = get_scenario_data(config.scenario_id or "austin_metro")
        boundary = scenario["city_boundary"]
        grid_nodes = scenario["power_grid_nodes"]
        demands = config.custom_demands if (config.custom_demands and len(config.custom_demands) > 0) else scenario["demand_points"]

        optimizer = PSOLocationOptimizer(
            config=config,
            city_boundary=boundary,
            demand_points=demands,
            grid_nodes=grid_nodes
        )
        result = optimizer.optimize()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PSO Optimization failed: {str(e)}")


@app.post("/api/baseline", response_model=OptimizationResult)
def run_baseline(config: PSOConfig = Body(...)):
    try:
        scenario = get_scenario_data(config.scenario_id or "austin_metro")
        boundary = scenario["city_boundary"]
        grid_nodes = scenario["power_grid_nodes"]
        demands = config.custom_demands if (config.custom_demands and len(config.custom_demands) > 0) else scenario["demand_points"]

        baseline_runner = BaselineRandomOptimizer(
            config=config,
            city_boundary=boundary,
            demand_points=demands,
            grid_nodes=grid_nodes
        )
        result = baseline_runner.run()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Baseline execution failed: {str(e)}")


@app.post("/api/compare", response_model=ComparisonResponse)
def run_full_comparison(config: PSOConfig = Body(...)):
    try:
        scenario = get_scenario_data(config.scenario_id or "austin_metro")
        boundary = scenario["city_boundary"]
        grid_nodes = scenario["power_grid_nodes"]
        demands = config.custom_demands if (config.custom_demands and len(config.custom_demands) > 0) else scenario["demand_points"]

        # Run PSO
        pso_optimizer = PSOLocationOptimizer(
            config=config,
            city_boundary=boundary,
            demand_points=demands,
            grid_nodes=grid_nodes
        )
        pso_res = pso_optimizer.optimize()

        # Run Random Baseline
        baseline_optimizer = BaselineRandomOptimizer(
            config=config,
            city_boundary=boundary,
            demand_points=demands,
            grid_nodes=grid_nodes
        )
        base_res = baseline_optimizer.run()

        # Compute Comparative Metrics
        comparison = compute_comparison_metrics(pso_res, base_res)

        return ComparisonResponse(
            pso=pso_res,
            baseline=base_res,
            comparison=comparison,
            city_boundary=boundary,
            power_grid_nodes=grid_nodes
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Comparison failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True, app_dir=str(BACKEND_DIR))

