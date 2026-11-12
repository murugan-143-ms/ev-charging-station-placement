import time
import numpy as np
from typing import List, Tuple
from app.models.schemas import (
    DemandPoint,
    Station,
    CityBoundary,
    PowerGridNode,
    PSOConfig,
    OptimizationResult,
    ComparisonMetric
)
from app.algorithm.pso import (
    point_in_polygon,
    repair_point_to_polygon,
    haversine_vectorized,
    estimate_station_cost
)


class BaselineRandomOptimizer:
    def __init__(
        self,
        config: PSOConfig,
        city_boundary: CityBoundary,
        demand_points: List[DemandPoint],
        grid_nodes: List[PowerGridNode],
    ):
        self.config = config
        self.boundary = city_boundary
        self.demand_points = demand_points
        self.grid_nodes = grid_nodes

        self.k = config.k_stations
        self.radius = config.service_radius_km

        if config.seed is not None:
            # Use offset seed for baseline so it is distinct but reproducible
            np.random.seed(config.seed + 999)

        self.demand_lats = np.array([dp.lat for dp in demand_points], dtype=np.float64)
        self.demand_lngs = np.array([dp.lng for dp in demand_points], dtype=np.float64)
        self.demand_weights = np.array([dp.weight for dp in demand_points], dtype=np.float64)
        self.total_demand_weight = float(np.sum(self.demand_weights))

        bb = self.boundary.bounding_box
        self.max_possible_dist = haversine_vectorized(
            np.array([bb["min_lat"]]), np.array([bb["min_lng"]]),
            np.array([bb["max_lat"]]), np.array([bb["max_lng"]])
        )[0, 0]
        if self.max_possible_dist <= 0:
            self.max_possible_dist = 25.0
        self.max_cost_per_station = 95000.0

    def generate_random_stations(self) -> np.ndarray:
        coords = np.zeros((self.k, 2), dtype=np.float64)
        bb = self.boundary.bounding_box
        polygon = self.boundary.polygon
        center = self.boundary.center

        for i in range(self.k):
            found = False
            for _ in range(100):
                lat = np.random.uniform(bb["min_lat"], bb["max_lat"])
                lng = np.random.uniform(bb["min_lng"], bb["max_lng"])
                if point_in_polygon(lat, lng, polygon):
                    coords[i, 0] = lat
                    coords[i, 1] = lng
                    found = True
                    break
            if not found:
                coords[i, 0], coords[i, 1] = repair_point_to_polygon(center[0], center[1], polygon, center)

        return coords

    def run(self) -> OptimizationResult:
        start_time = time.perf_counter()
        coords = self.generate_random_stations()

        st_lats = coords[:, 0]
        st_lngs = coords[:, 1]

        dist_matrix = haversine_vectorized(self.demand_lats, self.demand_lngs, st_lats, st_lngs)
        nearest_dists = np.min(dist_matrix, axis=1)
        nearest_idx = np.argmin(dist_matrix, axis=1)

        weighted_avg_dist = float(np.sum(self.demand_weights * nearest_dists) / self.total_demand_weight)

        covered_mask = nearest_dists <= self.radius
        covered_weight = float(np.sum(self.demand_weights[covered_mask]))
        coverage_pct = (covered_weight / self.total_demand_weight) * 100.0
        coverage_deficit = 1.0 - (covered_weight / self.total_demand_weight)

        costs = [
            estimate_station_cost(st_lats[i], st_lngs[i], self.grid_nodes, self.boundary.center)
            for i in range(self.k)
        ]
        total_cost = float(sum(costs))

        norm_dist = min(1.0, weighted_avg_dist / self.max_possible_dist)
        norm_cost = min(1.0, total_cost / (self.k * self.max_cost_per_station))

        fitness = (
            (self.config.weight_distance * norm_dist)
            + (self.config.weight_coverage * coverage_deficit)
            + (self.config.weight_cost * norm_cost)
        )

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        # Build stations & demands
        enriched_demands: List[DemandPoint] = []
        station_demands = {i: [] for i in range(self.k)}

        for j, dp in enumerate(self.demand_points):
            s_i = int(nearest_idx[j])
            d_km = float(nearest_dists[j])
            enriched_demands.append(
                DemandPoint(
                    id=dp.id,
                    name=dp.name,
                    lat=dp.lat,
                    lng=dp.lng,
                    weight=dp.weight,
                    category=dp.category,
                    expected_ev_count=dp.expected_ev_count,
                    is_covered=d_km <= self.radius,
                    nearest_station_id=f"rand-station-{s_i + 1}",
                    distance_to_nearest_station_km=round(d_km, 3),
                )
            )
            station_demands[s_i].append((dp.weight, d_km))

        stations: List[Station] = []
        for i in range(self.k):
            lat = float(st_lats[i])
            lng = float(st_lngs[i])
            demands = station_demands[i]
            cov_count = sum(1 for w, d in demands if d <= self.radius)
            total_w = sum(w for w, d in demands)
            avg_d = sum(d for w, d in demands) / max(1, len(demands))

            stations.append(
                Station(
                    id=f"rand-station-{i + 1}",
                    lat=round(lat, 5),
                    lng=round(lng, 5),
                    installation_cost=costs[i],
                    covered_demand_count=cov_count,
                    served_total_weight=round(total_w, 1),
                    avg_distance_to_assigned_demands_km=round(avg_d, 3),
                )
            )

        return OptimizationResult(
            algorithm_name="Baseline (Random Placement)",
            stations=stations,
            demand_points=enriched_demands,
            avg_distance_km=round(weighted_avg_dist, 3),
            coverage_pct=round(coverage_pct, 2),
            total_cost=round(total_cost, 2),
            fitness=round(fitness, 5),
            computation_time_ms=round(elapsed_ms, 2),
            iterations_run=1,
            convergence_history=[],
        )


def compute_comparison_metrics(pso_res: OptimizationResult, base_res: OptimizationResult) -> ComparisonMetric:
    base_dist = max(0.001, base_res.avg_distance_km)
    dist_reduction_pct = ((base_dist - pso_res.avg_distance_km) / base_dist) * 100.0

    coverage_gain_pct = pso_res.coverage_pct - base_res.coverage_pct

    cost_delta_pct = 0.0
    if base_res.total_cost > 0:
        cost_delta_pct = ((pso_res.total_cost - base_res.total_cost) / base_res.total_cost) * 100.0

    base_fit = max(0.0001, base_res.fitness)
    fit_improve_pct = ((base_fit - pso_res.fitness) / base_fit) * 100.0

    summary_text = (
        f"PSO achieved {dist_reduction_pct:+.1f}% distance reduction, "
        f"{coverage_gain_pct:+.1f}% higher coverage ({pso_res.coverage_pct:.1f}% vs {base_res.coverage_pct:.1f}%), "
        f"and improved overall objective fitness by {fit_improve_pct:+.1f}% compared to random baseline."
    )

    return ComparisonMetric(
        distance_reduction_pct=round(dist_reduction_pct, 2),
        coverage_gain_pct=round(coverage_gain_pct, 2),
        cost_delta_pct=round(cost_delta_pct, 2),
        fitness_improvement_pct=round(fit_improve_pct, 2),
        summary=summary_text,
    )

