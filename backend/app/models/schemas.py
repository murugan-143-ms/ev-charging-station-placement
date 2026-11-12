from typing import List, Optional, Tuple
from pydantic import BaseModel, Field


class DemandPoint(BaseModel):
    id: str
    name: str
    lat: float
    lng: float
    weight: float = Field(..., description="EV demand intensity / population weight (e.g., 10-100)")
    category: str = Field(..., description="Residential, Commercial Hub, Tech Park, Retail Mall, Transit Station, Airport/Logistics")
    expected_ev_count: int = Field(default=50)
    is_covered: Optional[bool] = False
    nearest_station_id: Optional[str] = None
    distance_to_nearest_station_km: Optional[float] = None


class PowerGridNode(BaseModel):
    id: str
    name: str
    lat: float
    lng: float
    voltage_kv: int = 110


class CityBoundary(BaseModel):
    name: str
    polygon: List[List[float]] = Field(..., description="List of [lat, lng] coordinates forming a closed boundary")
    center: List[float] = Field(..., description="[lat, lng] center coordinate")
    bounding_box: dict = Field(..., description="{min_lat, max_lat, min_lng, max_lng}")


class Station(BaseModel):
    id: str
    lat: float
    lng: float
    installation_cost: float
    covered_demand_count: int = 0
    served_total_weight: float = 0.0
    avg_distance_to_assigned_demands_km: float = 0.0


class PSOConfig(BaseModel):
    k_stations: int = Field(default=6, ge=2, le=25, description="Number of EV charging stations to place")
    service_radius_km: float = Field(default=3.5, ge=0.5, le=15.0, description="Service coverage radius R in km")
    swarm_size: int = Field(default=30, ge=10, le=100, description="Number of particles in swarm")
    max_iterations: int = Field(default=40, ge=10, le=150, description="Max PSO iterations")
    w_max: float = Field(default=0.9, ge=0.1, le=1.5, description="Initial maximum inertia weight")
    w_min: float = Field(default=0.4, ge=0.0, le=1.0, description="Final minimum inertia weight")
    c1: float = Field(default=2.0, ge=0.1, le=4.0, description="Cognitive acceleration coefficient")
    c2: float = Field(default=2.0, ge=0.1, le=4.0, description="Social acceleration coefficient")
    weight_distance: float = Field(default=0.45, ge=0.0, le=1.0, description="Weight for minimizing average distance")
    weight_coverage: float = Field(default=0.40, ge=0.0, le=1.0, description="Weight for maximizing coverage")
    weight_cost: float = Field(default=0.15, ge=0.0, le=1.0, description="Weight for minimizing installation cost")
    seed: Optional[int] = Field(default=None, description="Random seed for reproducibility")
    scenario_id: Optional[str] = Field(default="austin_metro", description="City scenario key")
    custom_demands: Optional[List[DemandPoint]] = None


class IterationMetric(BaseModel):
    iteration: int
    best_fitness: float
    avg_distance_km: float
    coverage_pct: float
    total_cost: float


class OptimizationResult(BaseModel):
    algorithm_name: str
    stations: List[Station]
    demand_points: List[DemandPoint]
    avg_distance_km: float
    coverage_pct: float
    total_cost: float
    fitness: float
    computation_time_ms: float
    iterations_run: int
    convergence_history: List[IterationMetric] = []


class ComparisonMetric(BaseModel):
    distance_reduction_pct: float
    coverage_gain_pct: float
    cost_delta_pct: float
    fitness_improvement_pct: float
    summary: str


class ComparisonResponse(BaseModel):
    pso: OptimizationResult
    baseline: OptimizationResult
    comparison: ComparisonMetric
    city_boundary: CityBoundary
    power_grid_nodes: List[PowerGridNode]

