import time
import math
import numpy as np
from typing import List, Tuple, Dict, Any, Optional
from app.models.schemas import (
    DemandPoint,
    Station,
    CityBoundary,
    PowerGridNode,
    PSOConfig,
    IterationMetric,
    OptimizationResult
)


def point_in_polygon(lat: float, lng: float, polygon: List[List[float]]) -> bool:
    """Ray casting algorithm to determine if a point (lat, lng) is inside a polygon."""
    n = len(polygon)
    inside = False
    p1x, p1y = polygon[0][0], polygon[0][1]
    for i in range(1, n + 1):
        p2x, p2y = polygon[i % n][0], polygon[i % n][1]
        if min(p1y, p2y) < lng <= max(p1y, p2y):
            # Point is within the latitude range of edge
            if lat <= max(p1x, p2x):
                if p1y != p2y:
                    xinters = (lng - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or lat <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y
    return inside


def repair_point_to_polygon(lat: float, lng: float, polygon: List[List[float]], center: List[float]) -> Tuple[float, float]:
    """
    If (lat, lng) is outside the polygon, snaps it along the ray toward the centroid
    until it falls safely inside the polygon boundary.
    """
    if point_in_polygon(lat, lng, polygon):
        return lat, lng

    c_lat, c_lng = center[0], center[1]
    # Binary search along the segment between (lat, lng) and center
    low = 0.0  # at center (guaranteed inside)
    high = 1.0 # at outside point
    
    # Check if center itself is inside (fallback to first vertex if somehow not)
    if not point_in_polygon(c_lat, c_lng, polygon):
        c_lat, c_lng = polygon[0][0], polygon[0][1]

    best_lat, best_lng = c_lat, c_lng
    for _ in range(25):
        mid = (low + high) / 2.0
        cur_lat = c_lat + (lat - c_lat) * mid
        cur_lng = c_lng + (lng - c_lng) * mid
        if point_in_polygon(cur_lat, cur_lng, polygon):
            best_lat, best_lng = cur_lat, cur_lng
            low = mid # try to get closer to the requested outside point
        else:
            high = mid

    # Apply small inward cushion (0.95 factor toward center)
    cushion_lat = c_lat + (best_lat - c_lat) * 0.96
    cushion_lng = c_lng + (best_lng - c_lng) * 0.96
    if point_in_polygon(cushion_lat, cushion_lng, polygon):
        return cushion_lat, cushion_lng
    return best_lat, best_lng


def haversine_vectorized(lats1: np.ndarray, lngs1: np.ndarray, lats2: np.ndarray, lngs2: np.ndarray) -> np.ndarray:
    """
    Computes pairwise Haversine distance in kilometers between N points (lats1, lngs1)
    and K points (lats2, lngs2). Output shape: (N, K).
    """
    R_EARTH = 6371.0 # km
    lat1_rad = np.radians(lats1)[:, np.newaxis]
    lng1_rad = np.radians(lngs1)[:, np.newaxis]
    lat2_rad = np.radians(lats2)[np.newaxis, :]
    lng2_rad = np.radians(lngs2)[np.newaxis, :]

    dlat = lat2_rad - lat1_rad
    dlng = lng2_rad - lng1_rad

    a = np.sin(dlat / 2.0) ** 2 + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlng / 2.0) ** 2
    c = 2.0 * np.arcsin(np.sqrt(np.clip(a, 0.0, 1.0)))
    return R_EARTH * c


def estimate_station_cost(lat: float, lng: float, grid_nodes: List[PowerGridNode], center: List[float]) -> float:
    """
    Computes realistic charging station installation cost:
    Base Hardware & Civil Works: $45,000
    Land Zone Multiplier (based on urban density / distance to center): 1.0 to 1.45
    Grid Connection Cost: $6,500 per km from nearest high-voltage grid substation.
    """
    BASE_COST = 45000.0
    GRID_COST_PER_KM = 6500.0

    # Distance to center for land cost factor
    d_lat = lat - center[0]
    d_lng = lng - center[1]
    dist_center_approx = math.sqrt(d_lat**2 + d_lng**2) * 111.0 # approx km
    # closer to center = higher land lease / civil permit fees
    land_factor = 1.0 + 0.45 * max(0.0, 1.0 - (dist_center_approx / 15.0))

    # Distance to nearest grid node
    min_grid_dist = 999.0
    for node in grid_nodes:
        dist = haversine_vectorized(np.array([lat]), np.array([lng]), np.array([node.lat]), np.array([node.lng]))[0, 0]
        if dist < min_grid_dist:
            min_grid_dist = dist

    total_cost = (BASE_COST * land_factor) + (GRID_COST_PER_KM * min_grid_dist)
    return round(float(total_cost), 2)


class PSOLocationOptimizer:
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
        self.swarm_size = config.swarm_size
        self.max_iter = config.max_iterations

        if config.seed is not None:
            np.random.seed(config.seed)

        # Precompute demand point arrays for vectorization
        self.demand_lats = np.array([dp.lat for dp in demand_points], dtype=np.float64)
        self.demand_lngs = np.array([dp.lng for dp in demand_points], dtype=np.float64)
        self.demand_weights = np.array([dp.weight for dp in demand_points], dtype=np.float64)
        self.total_demand_weight = float(np.sum(self.demand_weights))

        # Maximum possible distance across bounding box diagonal for normalization
        bb = self.boundary.bounding_box
        self.max_possible_dist = haversine_vectorized(
            np.array([bb["min_lat"]]), np.array([bb["min_lng"]]),
            np.array([bb["max_lat"]]), np.array([bb["max_lng"]])
        )[0, 0]
        if self.max_possible_dist <= 0:
            self.max_possible_dist = 25.0

        # Maximum expected cost per station for normalization
        self.max_cost_per_station = 95000.0

        # Coordinate spans for velocity clamping
        self.lat_span = bb["max_lat"] - bb["min_lat"]
        self.lng_span = bb["max_lng"] - bb["min_lng"]
        self.v_max_lat = 0.18 * self.lat_span
        self.v_max_lng = 0.18 * self.lng_span

    def evaluate_solution(self, station_coords: np.ndarray) -> Tuple[float, float, float, float]:
        """
        Evaluates a candidate solution of K stations:
        station_coords: shape (K, 2) where col 0 is lat, col 1 is lng.
        Returns:
            fitness, avg_distance_km, coverage_pct, total_cost
        """
        st_lats = station_coords[:, 0]
        st_lngs = station_coords[:, 1]

        # Pairwise distance (N_demands, K_stations)
        dist_matrix = haversine_vectorized(self.demand_lats, self.demand_lngs, st_lats, st_lngs)

        # Nearest station distance for each demand point
        nearest_dists = np.min(dist_matrix, axis=1)

        # Weighted average distance
        weighted_avg_dist = float(np.sum(self.demand_weights * nearest_dists) / self.total_demand_weight)

        # Coverage evaluation: demand points within radius R
        covered_mask = nearest_dists <= self.radius
        covered_weight = float(np.sum(self.demand_weights[covered_mask]))
        coverage_pct = (covered_weight / self.total_demand_weight) * 100.0
        coverage_deficit = 1.0 - (covered_weight / self.total_demand_weight)

        # Cost evaluation
        costs = [
            estimate_station_cost(st_lats[i], st_lngs[i], self.grid_nodes, self.boundary.center)
            for i in range(self.k)
        ]
        total_cost = float(sum(costs))

        # Normalized fitness metrics
        norm_dist = min(1.0, weighted_avg_dist / self.max_possible_dist)
        norm_cost = min(1.0, total_cost / (self.k * self.max_cost_per_station))

        w_dist = self.config.weight_distance
        w_cov = self.config.weight_coverage
        w_cost = self.config.weight_cost

        # Combined multi-objective fitness (Lower is better)
        fitness = (w_dist * norm_dist) + (w_cov * coverage_deficit) + (w_cost * norm_cost)

        return fitness, weighted_avg_dist, coverage_pct, total_cost

    def initialize_particle(self) -> np.ndarray:
        """Initializes K station coordinates strictly inside the city polygon."""
        coords = np.zeros((self.k, 2), dtype=np.float64)
        bb = self.boundary.bounding_box
        polygon = self.boundary.polygon
        center = self.boundary.center

        for i in range(self.k):
            # Try rejection sampling with fallback
            found = False
            for _ in range(60):
                lat = np.random.uniform(bb["min_lat"], bb["max_lat"])
                lng = np.random.uniform(bb["min_lng"], bb["max_lng"])
                if point_in_polygon(lat, lng, polygon):
                    coords[i, 0] = lat
                    coords[i, 1] = lng
                    found = True
                    break
            if not found:
                # Random blend towards centroid
                t = np.random.uniform(0.1, 0.85)
                v = polygon[i % len(polygon)]
                coords[i, 0] = center[0] + (v[0] - center[0]) * t
                coords[i, 1] = center[1] + (v[1] - center[1]) * t
                coords[i, 0], coords[i, 1] = repair_point_to_polygon(coords[i, 0], coords[i, 1], polygon, center)

        return coords

    def optimize(self) -> OptimizationResult:
        start_time = time.perf_counter()

        # Particles: shape (swarm_size, K, 2)
        particles = np.zeros((self.swarm_size, self.k, 2), dtype=np.float64)
        velocities = np.zeros((self.swarm_size, self.k, 2), dtype=np.float64)

        # Personal bests
        pbest_positions = np.zeros_like(particles)
        pbest_fitness = np.full(self.swarm_size, float("inf"), dtype=np.float64)

        # Global best
        gbest_position = np.zeros((self.k, 2), dtype=np.float64)
        gbest_fitness = float("inf")
        gbest_avg_dist = 0.0
        gbest_coverage_pct = 0.0
        gbest_cost = 0.0

        polygon = self.boundary.polygon
        center = self.boundary.center

        # Swarm initialization
        for p in range(self.swarm_size):
            particles[p] = self.initialize_particle()
            velocities[p, :, 0] = np.random.uniform(-0.1 * self.v_max_lat, 0.1 * self.v_max_lat, size=self.k)
            velocities[p, :, 1] = np.random.uniform(-0.1 * self.v_max_lng, 0.1 * self.v_max_lng, size=self.k)

            fit, avg_d, cov_p, cost_t = self.evaluate_solution(particles[p])
            pbest_positions[p] = np.copy(particles[p])
            pbest_fitness[p] = fit

            if fit < gbest_fitness:
                gbest_fitness = fit
                gbest_position = np.copy(particles[p])
                gbest_avg_dist = avg_d
                gbest_coverage_pct = cov_p
                gbest_cost = cost_t

        convergence_history: List[IterationMetric] = []
        convergence_history.append(
            IterationMetric(
                iteration=0,
                best_fitness=round(gbest_fitness, 5),
                avg_distance_km=round(gbest_avg_dist, 3),
                coverage_pct=round(gbest_coverage_pct, 2),
                total_cost=round(gbest_cost, 2),
            )
        )

        w_max = self.config.w_max
        w_min = self.config.w_min
        c1 = self.config.c1
        c2 = self.config.c2

        # Main PSO Iteration Loop
        for it in range(1, self.max_iter + 1):
            # Linearly decreasing inertia weight for optimal exploration-to-exploitation transition
            w = w_max - (it / float(self.max_iter)) * (w_max - w_min)

            for p in range(self.swarm_size):
                # Stochastic vectors
                r1 = np.random.uniform(0.0, 1.0, size=(self.k, 2))
                r2 = np.random.uniform(0.0, 1.0, size=(self.k, 2))

                # Standard PSO Velocity Update Equation
                # V(t+1) = w*V(t) + c1*r1*(pbest - X) + c2*r2*(gbest - X)
                cognitive = c1 * r1 * (pbest_positions[p] - particles[p])
                social = c2 * r2 * (gbest_position - particles[p])
                velocities[p] = w * velocities[p] + cognitive + social

                # Clamp velocities
                velocities[p, :, 0] = np.clip(velocities[p, :, 0], -self.v_max_lat, self.v_max_lat)
                velocities[p, :, 1] = np.clip(velocities[p, :, 1], -self.v_max_lng, self.v_max_lng)

                # Position Update Equation: X(t+1) = X(t) + V(t+1)
                particles[p] += velocities[p]

                # Boundary Constraint Enforcement: Clamp & Repair to City Polygon
                for k_idx in range(self.k):
                    lat = particles[p, k_idx, 0]
                    lng = particles[p, k_idx, 1]
                    if not point_in_polygon(lat, lng, polygon):
                        rep_lat, rep_lng = repair_point_to_polygon(lat, lng, polygon, center)
                        particles[p, k_idx, 0] = rep_lat
                        particles[p, k_idx, 1] = rep_lng
                        # Bounce velocity component
                        velocities[p, k_idx, 0] *= -0.5
                        velocities[p, k_idx, 1] *= -0.5

                # Evaluate new particle fitness
                fit, avg_d, cov_p, cost_t = self.evaluate_solution(particles[p])

                # Update Personal Best
                if fit < pbest_fitness[p]:
                    pbest_fitness[p] = fit
                    pbest_positions[p] = np.copy(particles[p])

                    # Update Global Best
                    if fit < gbest_fitness:
                        gbest_fitness = fit
                        gbest_position = np.copy(particles[p])
                        gbest_avg_dist = avg_d
                        gbest_coverage_pct = cov_p
                        gbest_cost = cost_t

            # Record iteration history
            convergence_history.append(
                IterationMetric(
                    iteration=it,
                    best_fitness=round(gbest_fitness, 5),
                    avg_distance_km=round(gbest_avg_dist, 3),
                    coverage_pct=round(gbest_coverage_pct, 2),
                    total_cost=round(gbest_cost, 2),
                )
            )

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        # Construct finalized station objects and enrich demand point associations
        final_stations, final_demands = self._build_solution_details(gbest_position)

        return OptimizationResult(
            algorithm_name="Particle Swarm Optimization (PSO)",
            stations=final_stations,
            demand_points=final_demands,
            avg_distance_km=round(gbest_avg_dist, 3),
            coverage_pct=round(gbest_coverage_pct, 2),
            total_cost=round(gbest_cost, 2),
            fitness=round(gbest_fitness, 5),
            computation_time_ms=round(elapsed_ms, 2),
            iterations_run=self.max_iter,
            convergence_history=convergence_history,
        )

    def _build_solution_details(self, station_coords: np.ndarray) -> Tuple[List[Station], List[DemandPoint]]:
        """Associates demand points with nearest stations and computes station service loads."""
        st_lats = station_coords[:, 0]
        st_lngs = station_coords[:, 1]

        dist_matrix = haversine_vectorized(self.demand_lats, self.demand_lngs, st_lats, st_lngs)
        nearest_station_indices = np.argmin(dist_matrix, axis=1)
        nearest_station_distances = np.min(dist_matrix, axis=1)

        enriched_demands: List[DemandPoint] = []
        station_demands: Dict[int, List[Tuple[float, float]]] = {i: [] for i in range(self.k)}

        for j, dp in enumerate(self.demand_points):
            st_idx = int(nearest_station_indices[j])
            dist_km = float(nearest_station_distances[j])
            is_cov = dist_km <= self.radius

            enriched_demands.append(
                DemandPoint(
                    id=dp.id,
                    name=dp.name,
                    lat=dp.lat,
                    lng=dp.lng,
                    weight=dp.weight,
                    category=dp.category,
                    expected_ev_count=dp.expected_ev_count,
                    is_covered=is_cov,
                    nearest_station_id=f"station-{st_idx + 1}",
                    distance_to_nearest_station_km=round(dist_km, 3),
                )
            )
            station_demands[st_idx].append((dp.weight, dist_km))

        stations: List[Station] = []
        for i in range(self.k):
            lat = float(st_lats[i])
            lng = float(st_lngs[i])
            cost = estimate_station_cost(lat, lng, self.grid_nodes, self.boundary.center)
            
            demands_for_st = station_demands[i]
            cov_count = sum(1 for w, d in demands_for_st if d <= self.radius)
            total_w = sum(w for w, d in demands_for_st)
            avg_d = sum(d for w, d in demands_for_st) / max(1, len(demands_for_st))

            stations.append(
                Station(
                    id=f"station-{i + 1}",
                    lat=round(lat, 5),
                    lng=round(lng, 5),
                    installation_cost=cost,
                    covered_demand_count=cov_count,
                    served_total_weight=round(total_w, 1),
                    avg_distance_to_assigned_demands_km=round(avg_d, 3),
                )
            )

        return stations, enriched_demands

