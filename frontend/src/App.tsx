import { useState, useEffect, useRef } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import {
  Zap,
  BatteryCharging,
  Sliders,
  Play,
  TrendingUp,
  MapPin,
  Activity,
  RefreshCw,
  Layers
} from 'lucide-react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  Legend
} from 'recharts';

interface DemandPoint {
  id: string;
  name: string;
  lat: number;
  lng: number;
  weight: number;
  category: string;
  expected_ev_count: number;
  is_covered?: boolean;
  nearest_station_id?: string;
  distance_to_nearest_station_km?: number;
}

interface PowerGridNode {
  id: string;
  name: string;
  lat: number;
  lng: number;
  voltage_kv: number;
}

interface CityBoundary {
  name: string;
  polygon: [number, number][];
  center: [number, number];
  bounding_box: {
    min_lat: number;
    max_lat: number;
    min_lng: number;
    max_lng: number;
  };
}

interface Station {
  id: string;
  lat: number;
  lng: number;
  installation_cost: number;
  covered_demand_count: number;
  served_total_weight: number;
  avg_distance_to_assigned_demands_km: number;
}

interface IterationMetric {
  iteration: number;
  best_fitness: number;
  avg_distance_km: number;
  coverage_pct: number;
  total_cost: number;
}

interface OptimizationResult {
  algorithm_name: string;
  stations: Station[];
  demand_points: DemandPoint[];
  avg_distance_km: number;
  coverage_pct: number;
  total_cost: number;
  fitness: number;
  computation_time_ms: number;
  iterations_run: number;
  convergence_history: IterationMetric[];
}

interface ComparisonMetric {
  distance_reduction_pct: number;
  coverage_gain_pct: number;
  cost_delta_pct: number;
  fitness_improvement_pct: number;
  summary: string;
}

interface ComparisonResponse {
  pso: OptimizationResult;
  baseline: OptimizationResult;
  comparison: ComparisonMetric;
  city_boundary: CityBoundary;
  power_grid_nodes: PowerGridNode[];
}

const API_BASE = "http://127.0.0.1:8000";

export default function App() {
  // Config state
  const [scenarioId, setScenarioId] = useState<string>("austin_metro");
  const [kStations, setKStations] = useState<number>(6);
  const [serviceRadiusKm, setServiceRadiusKm] = useState<number>(3.5);
  const [swarmSize, setSwarmSize] = useState<number>(30);
  const [maxIterations, setMaxIterations] = useState<number>(45);
  const [weightDistance, setWeightDistance] = useState<number>(0.45);
  const [weightCoverage, setWeightCoverage] = useState<number>(0.40);
  const [weightCost, setWeightCost] = useState<number>(0.15);

  // Data state
  const [boundary, setBoundary] = useState<CityBoundary | null>(null);
  const [demandPoints, setDemandPoints] = useState<DemandPoint[]>([]);
  const [gridNodes, setGridNodes] = useState<PowerGridNode[]>([]);
  const [psoResult, setPsoResult] = useState<OptimizationResult | null>(null);
  const [baselineResult, setBaselineResult] = useState<OptimizationResult | null>(null);
  const [comparisonMetrics, setComparisonMetrics] = useState<ComparisonMetric | null>(null);

  // UI state
  const [loading, setLoading] = useState<boolean>(false);
  const [showBaselineOverlay, setShowBaselineOverlay] = useState<boolean>(false);
  const [showRadiusCircles, setShowRadiusCircles] = useState<boolean>(true);
  const [activeTab, setActiveTab] = useState<'map' | 'convergence' | 'stations'>('map');
  const [apiConnected, setApiConnected] = useState<boolean | null>(null);

  // Map references
  const mapContainerRef = useRef<HTMLDivElement | null>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const layerGroupRef = useRef<L.LayerGroup | null>(null);

  // Initialize or fetch initial scenario data
  const loadScenarioData = async (selectedScenario: string) => {
    try {
      const res = await fetch(`${API_BASE}/api/scenario-data?scenario_id=${selectedScenario}`);
      if (!res.ok) throw new Error("Failed to fetch scenario");
      const data = await res.json();
      setBoundary(data.city_boundary);
      setDemandPoints(data.demand_points);
      setGridNodes(data.power_grid_nodes);
      setPsoResult(null);
      setBaselineResult(null);
      setComparisonMetrics(null);
      setApiConnected(true);
    } catch (err) {
      console.warn("Backend not reached at", API_BASE, err);
      setApiConnected(false);
    }
  };

  useEffect(() => {
    loadScenarioData(scenarioId);
  }, [scenarioId]);

  // Setup Leaflet Map
  useEffect(() => {
    if (!mapContainerRef.current) return;

    if (!mapInstanceRef.current) {
      const map = L.map(mapContainerRef.current, {
        zoomControl: true,
        attributionControl: false
      }).setView([30.2747, -97.7404], 11);

      L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
        maxZoom: 19
      }).addTo(map);

      const layers = L.layerGroup().addTo(map);
      layerGroupRef.current = layers;
      mapInstanceRef.current = map;
    }

    return () => {
      // Keep map instance mounted across tab toggles
    };
  }, []);

  // Update map contents whenever data or results change
  useEffect(() => {
    const map = mapInstanceRef.current;
    const layerGroup = layerGroupRef.current;
    if (!map || !layerGroup) return;

    layerGroup.clearLayers();

    // 1. Draw City Boundary Polygon
    if (boundary && boundary.polygon.length > 0) {
      const polyCoords = boundary.polygon.map(pt => [pt[0], pt[1]] as [number, number]);
      const polygon = L.polygon(polyCoords, {
        color: '#3b82f6',
        weight: 2,
        fillColor: '#60a5fa',
        fillOpacity: 0.08,
        dashArray: '4, 4'
      }).addTo(layerGroup);

      map.fitBounds(polygon.getBounds(), { padding: [25, 25] });
    }

    // 2. Draw Power Grid Nodes (Substations)
    gridNodes.forEach(node => {
      const iconHtml = `<div class="w-5 h-5 rounded-full bg-amber-500 border-2 border-white shadow-md flex items-center justify-center text-[10px] text-white font-bold">⚡</div>`;
      const customIcon = L.divIcon({
        className: 'custom-grid-marker',
        html: iconHtml,
        iconSize: [20, 20],
        iconAnchor: [10, 10]
      });

      L.marker([node.lat, node.lng], { icon: customIcon })
        .bindPopup(`
          <div class="p-1">
            <div class="font-bold text-slate-800 text-xs">⚡ ${node.name}</div>
            <div class="text-[11px] text-slate-500">Power Grid Substation (${node.voltage_kv} kV)</div>
            <div class="text-[11px] text-slate-400 mt-1">Coord: ${node.lat.toFixed(4)}, ${node.lng.toFixed(4)}</div>
          </div>
        `)
        .addTo(layerGroup);
    });

    // 3. Draw EV Demand Points
    const currentDemands = psoResult ? psoResult.demand_points : demandPoints;
    currentDemands.forEach(dp => {
      const isCovered = dp.is_covered ?? false;
      const markerColor = isCovered ? '#10b981' : '#94a3b8';
      const borderColor = isCovered ? '#047857' : '#64748b';

      const circle = L.circleMarker([dp.lat, dp.lng], {
        radius: Math.min(8, Math.max(4, dp.weight / 15)),
        fillColor: markerColor,
        color: borderColor,
        weight: 1.5,
        opacity: 0.9,
        fillOpacity: isCovered ? 0.75 : 0.4
      });

      circle.bindPopup(`
        <div class="p-1">
          <div class="font-bold text-slate-900 text-xs">${dp.name}</div>
          <div class="text-[11px] font-medium text-emerald-600">${dp.category}</div>
          <div class="text-[11px] text-slate-600 mt-1">Intensity Weight: <b>${dp.weight}</b> | Expected EVs: <b>${dp.expected_ev_count}</b></div>
          <div class="text-[11px] mt-1 ${isCovered ? 'text-emerald-700 font-semibold' : 'text-rose-600 font-semibold'}">
            ${isCovered ? `✓ Covered (${dp.distance_to_nearest_station_km} km to ${dp.nearest_station_id})` : '✕ Outside Charging Radius'}
          </div>
        </div>
      `);
      circle.addTo(layerGroup);
    });

    // 4. Draw Baseline (Random) Stations if overlay enabled
    if (showBaselineOverlay && baselineResult) {
      baselineResult.stations.forEach((st, idx) => {
        const baseIconHtml = `
          <div class="w-7 h-7 rounded-full bg-rose-500 border-2 border-white shadow-lg flex items-center justify-center text-white font-bold text-xs ring-2 ring-rose-300">
            B${idx + 1}
          </div>
        `;
        const baseIcon = L.divIcon({
          className: 'base-marker',
          html: baseIconHtml,
          iconSize: [28, 28],
          iconAnchor: [14, 14]
        });

        L.marker([st.lat, st.lng], { icon: baseIcon })
          .bindPopup(`
            <div class="p-1">
              <span class="px-1.5 py-0.5 rounded text-[10px] font-bold bg-rose-100 text-rose-800">Random Baseline</span>
              <div class="font-bold text-slate-900 mt-1">${st.id}</div>
              <div class="text-[11px] text-slate-600">Cost: $${st.installation_cost.toLocaleString()}</div>
              <div class="text-[11px] text-slate-600">Covered Demands: ${st.covered_demand_count}</div>
            </div>
          `)
          .addTo(layerGroup);

        if (showRadiusCircles) {
          L.circle([st.lat, st.lng], {
            radius: serviceRadiusKm * 1000,
            color: '#f43f5e',
            weight: 1,
            fillColor: '#f43f5e',
            fillOpacity: 0.05,
            dashArray: '3, 4'
          }).addTo(layerGroup);
        }
      });
    }

    // 5. Draw Optimized PSO Stations
    if (psoResult && psoResult.stations.length > 0) {
      psoResult.stations.forEach((st, idx) => {
        const psoIconHtml = `
          <div class="w-8 h-8 rounded-full bg-emerald-600 border-2 border-white shadow-xl flex items-center justify-center text-white font-bold text-xs ring-4 ring-emerald-300/60 animate-bounce-once">
            S${idx + 1}
          </div>
        `;
        const psoIcon = L.divIcon({
          className: 'pso-marker',
          html: psoIconHtml,
          iconSize: [32, 32],
          iconAnchor: [16, 16]
        });

        const marker = L.marker([st.lat, st.lng], { icon: psoIcon });
        marker.bindPopup(`
          <div class="p-1">
            <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800">PSO Station ${idx + 1}</span>
            <div class="font-bold text-slate-900 text-sm mt-1">${st.id}</div>
            <div class="text-xs text-slate-600 mt-0.5">Est. Cost: <b class="text-slate-900">$${st.installation_cost.toLocaleString()}</b></div>
            <div class="text-xs text-slate-600">Covered Zones: <b class="text-emerald-700">${st.covered_demand_count}</b></div>
            <div class="text-xs text-slate-600">Total EV Load: <b class="text-slate-900">${st.served_total_weight.toFixed(1)}</b></div>
            <div class="text-xs text-slate-600">Avg Assigned Dist: <b>${st.avg_distance_to_assigned_demands_km} km</b></div>
            <div class="text-[10px] text-slate-400 mt-1">Coord: [${st.lat.toFixed(4)}, ${st.lng.toFixed(4)}]</div>
          </div>
        `);
        marker.addTo(layerGroup);

        // Coverage radius circle
        if (showRadiusCircles) {
          L.circle([st.lat, st.lng], {
            radius: serviceRadiusKm * 1000,
            color: '#10b981',
            weight: 1.5,
            fillColor: '#10b981',
            fillOpacity: 0.12
          }).addTo(layerGroup);
        }
      });
    }
  }, [boundary, gridNodes, demandPoints, psoResult, baselineResult, showBaselineOverlay, showRadiusCircles, serviceRadiusKm]);

  // Execute Optimization API Call
  const handleRunOptimization = async () => {
    setLoading(true);
    try {
      const payload = {
        scenario_id: scenarioId,
        k_stations: kStations,
        service_radius_km: serviceRadiusKm,
        swarm_size: swarmSize,
        max_iterations: maxIterations,
        weight_distance: weightDistance,
        weight_coverage: weightCoverage,
        weight_cost: weightCost
      };

      const res = await fetch(`${API_BASE}/api/compare`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      if (!res.ok) throw new Error("Optimization failed");
      const data: ComparisonResponse = await res.json();
      setPsoResult(data.pso);
      setBaselineResult(data.baseline);
      setComparisonMetrics(data.comparison);
      setApiConnected(true);
      setShowBaselineOverlay(true);
    } catch (err) {
      console.error("Optimization failed:", err);
      alert("Failed to connect to optimization API backend at http://127.0.0.1:8000. Ensure the backend server is running.");
      setApiConnected(false);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-screen w-screen bg-slate-900 text-slate-100 overflow-hidden font-sans">
      {/* Top Navbar */}
      <header className="h-14 border-b border-slate-800 bg-slate-950/80 backdrop-blur px-6 flex items-center justify-between shrink-0">
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 rounded-lg bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center text-emerald-400">
            <BatteryCharging className="w-5 h-5" />
          </div>
          <div>
            <h1 className="font-bold text-base tracking-tight text-white flex items-center gap-2">
              EV Charging Placement Optimizer
              <span className="text-[10px] font-semibold uppercase px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                PSO Multi-Objective
              </span>
            </h1>
          </div>
        </div>

        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2 text-xs">
            <span className="text-slate-400">API Status:</span>
            {apiConnected === true && (
              <span className="flex items-center text-emerald-400 gap-1 font-medium">
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span> Connected
              </span>
            )}
            {apiConnected === false && (
              <span className="flex items-center text-rose-400 gap-1 font-medium">
                <span className="w-2 h-2 rounded-full bg-rose-500"></span> Disconnected
              </span>
            )}
            {apiConnected === null && (
              <span className="flex items-center text-slate-500 gap-1">Checking...</span>
            )}
          </div>

          <button
            onClick={() => loadScenarioData(scenarioId)}
            className="p-1.5 rounded-md hover:bg-slate-800 text-slate-400 hover:text-white transition"
            title="Reset Scenario"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </header>

      {/* Main Grid: Left Controls (320px) | Right Map & Analytics */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Sidebar: Controls */}
        <aside className="w-84 border-r border-slate-800 bg-slate-950/50 flex flex-col shrink-0 overflow-y-auto">
          <div className="p-4 border-b border-slate-800/80">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5 mb-3">
              <Sliders className="w-3.5 h-3.5 text-emerald-400" /> Optimization Parameters
            </h2>

            {/* Scenario Selection */}
            <div className="space-y-1.5 mb-4">
              <label className="text-xs font-medium text-slate-300">City Corridor Scenario</label>
              <select
                value={scenarioId}
                onChange={(e) => setScenarioId(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded-md px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-emerald-500 transition"
              >
                <option value="austin_metro">Austin Metro (Texas EV Corridor)</option>
                <option value="san_francisco_bay">San Francisco Peninsula Grid</option>
              </select>
            </div>

            {/* Target Stations Slider */}
            <div className="space-y-1.5 mb-4">
              <div className="flex justify-between text-xs">
                <span className="text-slate-300">Charging Stations (k)</span>
                <span className="font-bold text-emerald-400">{kStations} stations</span>
              </div>
              <input
                type="range"
                min="2"
                max="12"
                value={kStations}
                onChange={(e) => setKStations(Number(e.target.value))}
                className="w-full accent-emerald-500 h-1.5 bg-slate-800 rounded-lg cursor-pointer"
              />
            </div>

            {/* Service Radius Slider */}
            <div className="space-y-1.5 mb-4">
              <div className="flex justify-between text-xs">
                <span className="text-slate-300">Service Radius (R)</span>
                <span className="font-bold text-emerald-400">{serviceRadiusKm.toFixed(1)} km</span>
              </div>
              <input
                type="range"
                min="1.0"
                max="8.0"
                step="0.5"
                value={serviceRadiusKm}
                onChange={(e) => setServiceRadiusKm(Number(e.target.value))}
                className="w-full accent-emerald-500 h-1.5 bg-slate-800 rounded-lg cursor-pointer"
              />
            </div>

            {/* Swarm Size Slider */}
            <div className="space-y-1.5 mb-4">
              <div className="flex justify-between text-xs">
                <span className="text-slate-300">PSO Swarm Size</span>
                <span className="font-bold text-emerald-400">{swarmSize} particles</span>
              </div>
              <input
                type="range"
                min="15"
                max="60"
                step="5"
                value={swarmSize}
                onChange={(e) => setSwarmSize(Number(e.target.value))}
                className="w-full accent-emerald-500 h-1.5 bg-slate-800 rounded-lg cursor-pointer"
              />
            </div>

            {/* Max Iterations */}
            <div className="space-y-1.5 mb-4">
              <div className="flex justify-between text-xs">
                <span className="text-slate-300">Max Iterations</span>
                <span className="font-bold text-emerald-400">{maxIterations} epochs</span>
              </div>
              <input
                type="range"
                min="15"
                max="100"
                step="5"
                value={maxIterations}
                onChange={(e) => setMaxIterations(Number(e.target.value))}
                className="w-full accent-emerald-500 h-1.5 bg-slate-800 rounded-lg cursor-pointer"
              />
            </div>

            {/* Multi-Objective Weights */}
            <div className="pt-2 border-t border-slate-800/60 space-y-3">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">Objective Weights</span>
              <div className="space-y-2">
                <div>
                  <div className="flex justify-between text-[11px] text-slate-400">
                    <span>Coverage Weight (w_cov)</span>
                    <span className="font-semibold text-white">{weightCoverage.toFixed(2)}</span>
                  </div>
                  <input
                    type="range"
                    min="0.1"
                    max="0.8"
                    step="0.05"
                    value={weightCoverage}
                    onChange={(e) => setWeightCoverage(Number(e.target.value))}
                    className="w-full accent-emerald-500 h-1 bg-slate-800 rounded-lg cursor-pointer"
                  />
                </div>
                <div>
                  <div className="flex justify-between text-[11px] text-slate-400">
                    <span>Distance Weight (w_dist)</span>
                    <span className="font-semibold text-white">{weightDistance.toFixed(2)}</span>
                  </div>
                  <input
                    type="range"
                    min="0.1"
                    max="0.8"
                    step="0.05"
                    value={weightDistance}
                    onChange={(e) => setWeightDistance(Number(e.target.value))}
                    className="w-full accent-emerald-500 h-1 bg-slate-800 rounded-lg cursor-pointer"
                  />
                </div>
                <div>
                  <div className="flex justify-between text-[11px] text-slate-400">
                    <span>Grid Cost Weight (w_cost)</span>
                    <span className="font-semibold text-white">{weightCost.toFixed(2)}</span>
                  </div>
                  <input
                    type="range"
                    min="0.05"
                    max="0.5"
                    step="0.05"
                    value={weightCost}
                    onChange={(e) => setWeightCost(Number(e.target.value))}
                    className="w-full accent-emerald-500 h-1 bg-slate-800 rounded-lg cursor-pointer"
                  />
                </div>
              </div>
            </div>

            {/* Run Button */}
            <button
              onClick={handleRunOptimization}
              disabled={loading}
              className="w-full mt-5 py-2.5 px-4 rounded-lg bg-emerald-600 hover:bg-emerald-500 active:bg-emerald-700 text-white font-semibold text-xs flex items-center justify-center gap-2 shadow-lg shadow-emerald-900/40 transition disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  Optimizing Swarm...
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 fill-white" />
                  Run PSO Optimization
                </>
              )}
            </button>
          </div>

          {/* Map Layer Toggles */}
          <div className="p-4 border-b border-slate-800/80 space-y-2">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
              <Layers className="w-3.5 h-3.5 text-blue-400" /> Map Overlays
            </span>
            <label className="flex items-center space-x-2 text-xs text-slate-300 cursor-pointer">
              <input
                type="checkbox"
                checked={showRadiusCircles}
                onChange={(e) => setShowRadiusCircles(e.target.checked)}
                className="rounded bg-slate-800 border-slate-700 text-emerald-500 focus:ring-emerald-500"
              />
              <span>Station Coverage Radii ({serviceRadiusKm} km)</span>
            </label>
            <label className="flex items-center space-x-2 text-xs text-slate-300 cursor-pointer">
              <input
                type="checkbox"
                checked={showBaselineOverlay}
                disabled={!baselineResult}
                onChange={(e) => setShowBaselineOverlay(e.target.checked)}
                className="rounded bg-slate-800 border-slate-700 text-rose-500 focus:ring-rose-500"
              />
              <span>Show Random Baseline (Red Markers)</span>
            </label>
          </div>

          {/* Legend */}
          <div className="p-4 text-xs space-y-2 text-slate-400">
            <div className="font-semibold text-slate-300 mb-1">Map Legend:</div>
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-emerald-500 border border-white"></span>
              <span>PSO Optimized Station (S#)</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-rose-500 border border-white"></span>
              <span>Random Baseline Station (B#)</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500"></span>
              <span>Covered EV Demand Node</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-slate-500"></span>
              <span>Uncovered Demand Node</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-[11px]">⚡</span>
              <span>Power Substation Node</span>
            </div>
          </div>
        </aside>

        {/* Right Section: Top Analytics Bar + Tabs (Map / Convergence / Stations) */}
        <div className="flex-1 flex flex-col overflow-hidden bg-slate-900">
          {/* Top Performance Metrics Banner */}
          <div className="h-20 bg-slate-950/70 border-b border-slate-800 px-6 flex items-center justify-between shrink-0 gap-4">
            <div className="grid grid-cols-4 gap-4 flex-1 max-w-4xl">
              {/* Coverage Metric */}
              <div className="bg-slate-900/90 border border-slate-800 rounded-lg p-2.5">
                <div className="text-[10px] uppercase font-bold text-slate-400">Demand Coverage</div>
                <div className="flex items-baseline gap-2 mt-0.5">
                  <span className="text-xl font-extrabold text-white">
                    {psoResult ? `${psoResult.coverage_pct.toFixed(1)}%` : '—'}
                  </span>
                  {comparisonMetrics && (
                    <span className="text-[11px] font-bold text-emerald-400">
                      +{comparisonMetrics.coverage_gain_pct.toFixed(1)}%
                    </span>
                  )}
                </div>
              </div>

              {/* Avg Distance Metric */}
              <div className="bg-slate-900/90 border border-slate-800 rounded-lg p-2.5">
                <div className="text-[10px] uppercase font-bold text-slate-400">Avg Travel Distance</div>
                <div className="flex items-baseline gap-2 mt-0.5">
                  <span className="text-xl font-extrabold text-white">
                    {psoResult ? `${psoResult.avg_distance_km.toFixed(2)} km` : '—'}
                  </span>
                  {comparisonMetrics && (
                    <span className="text-[11px] font-bold text-emerald-400">
                      -{comparisonMetrics.distance_reduction_pct.toFixed(1)}%
                    </span>
                  )}
                </div>
              </div>

              {/* Total Capital Cost */}
              <div className="bg-slate-900/90 border border-slate-800 rounded-lg p-2.5">
                <div className="text-[10px] uppercase font-bold text-slate-400">Estimated Cost</div>
                <div className="flex items-baseline gap-2 mt-0.5">
                  <span className="text-lg font-extrabold text-white">
                    {psoResult ? `$${Math.round(psoResult.total_cost).toLocaleString()}` : '—'}
                  </span>
                  {comparisonMetrics && (
                    <span className="text-[11px] font-bold text-emerald-400">
                      {comparisonMetrics.cost_delta_pct > 0 ? `+${comparisonMetrics.cost_delta_pct.toFixed(1)}%` : `${comparisonMetrics.cost_delta_pct.toFixed(1)}%`}
                    </span>
                  )}
                </div>
              </div>

              {/* Fitness & Runtime */}
              <div className="bg-slate-900/90 border border-slate-800 rounded-lg p-2.5">
                <div className="text-[10px] uppercase font-bold text-slate-400">Fitness / Speed</div>
                <div className="flex items-baseline gap-2 mt-0.5">
                  <span className="text-xl font-extrabold text-emerald-400">
                    {psoResult ? psoResult.fitness.toFixed(4) : '—'}
                  </span>
                  <span className="text-[11px] text-slate-400">
                    {psoResult ? `${psoResult.computation_time_ms.toFixed(0)} ms` : ''}
                  </span>
                </div>
              </div>
            </div>

            {/* Tab Switcher */}
            <div className="flex items-center space-x-1 bg-slate-900 p-1 rounded-lg border border-slate-800">
              <button
                onClick={() => setActiveTab('map')}
                className={`px-3 py-1.5 rounded-md text-xs font-semibold transition ${
                  activeTab === 'map' ? 'bg-emerald-600 text-white' : 'text-slate-400 hover:text-white'
                }`}
              >
                Interactive Map
              </button>
              <button
                onClick={() => setActiveTab('convergence')}
                className={`px-3 py-1.5 rounded-md text-xs font-semibold transition ${
                  activeTab === 'convergence' ? 'bg-emerald-600 text-white' : 'text-slate-400 hover:text-white'
                }`}
              >
                Convergence Curves
              </button>
              <button
                onClick={() => setActiveTab('stations')}
                className={`px-3 py-1.5 rounded-md text-xs font-semibold transition ${
                  activeTab === 'stations' ? 'bg-emerald-600 text-white' : 'text-slate-400 hover:text-white'
                }`}
              >
                Station Details
              </button>
            </div>
          </div>

          {/* Tab Views */}
          <div className="flex-1 relative overflow-hidden">
            {/* 1. Map Tab */}
            <div
              className={`w-full h-full ${activeTab === 'map' ? 'block' : 'hidden'}`}
              ref={mapContainerRef}
            />

            {/* 2. Convergence History Tab */}
            {activeTab === 'convergence' && (
              <div className="w-full h-full p-6 bg-slate-950 overflow-y-auto">
                <div className="max-w-5xl mx-auto space-y-6">
                  <div>
                    <h2 className="text-lg font-bold text-white flex items-center gap-2">
                      <TrendingUp className="w-5 h-5 text-emerald-400" /> PSO Swarm Convergence Trajectory
                    </h2>
                    <p className="text-xs text-slate-400 mt-1">
                      Tracks objective fitness minimization and coverage gains across all iterations.
                    </p>
                  </div>

                  {psoResult && psoResult.convergence_history.length > 0 ? (
                    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xl">
                      <div className="h-80 w-full">
                        <ResponsiveContainer width="100%" height="100%">
                          <LineChart data={psoResult.convergence_history}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                            <XAxis
                              dataKey="iteration"
                              stroke="#94a3b8"
                              label={{ value: 'Iteration', position: 'insideBottom', offset: -5, fill: '#94a3b8' }}
                            />
                            <YAxis yAxisId="left" stroke="#10b981" />
                            <YAxis yAxisId="right" orientation="right" stroke="#38bdf8" />
                            <RechartsTooltip
                              contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px' }}
                            />
                            <Legend />
                            <Line
                              yAxisId="left"
                              type="monotone"
                              dataKey="best_fitness"
                              name="Best Swarm Fitness (Minimize)"
                              stroke="#10b981"
                              strokeWidth={2.5}
                              dot={false}
                            />
                            <Line
                              yAxisId="right"
                              type="monotone"
                              dataKey="coverage_pct"
                              name="Coverage % (Maximize)"
                              stroke="#38bdf8"
                              strokeWidth={2}
                              dot={false}
                            />
                          </LineChart>
                        </ResponsiveContainer>
                      </div>
                    </div>
                  ) : (
                    <div className="p-12 text-center bg-slate-900/50 rounded-xl border border-slate-800">
                      <Activity className="w-8 h-8 text-slate-600 mx-auto mb-2" />
                      <div className="text-slate-400 text-sm font-medium">No convergence data yet</div>
                      <div className="text-slate-500 text-xs mt-1">
                        Click "Run PSO Optimization" in the sidebar to generate swarm convergence logs.
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* 3. Stations Details Tab */}
            {activeTab === 'stations' && (
              <div className="w-full h-full p-6 bg-slate-950 overflow-y-auto">
                <div className="max-w-5xl mx-auto space-y-6">
                  <div>
                    <h2 className="text-lg font-bold text-white flex items-center gap-2">
                      <Zap className="w-5 h-5 text-emerald-400" /> Optimal Station Placement Inventory
                    </h2>
                    <p className="text-xs text-slate-400 mt-1">
                      Individual coordinates, electrical substation connection distances, and assigned EV populations.
                    </p>
                  </div>

                  {psoResult ? (
                    <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-xl">
                      <table className="w-full text-left text-xs text-slate-300">
                        <thead className="bg-slate-800/80 uppercase font-semibold text-slate-400 text-[11px] border-b border-slate-700">
                          <tr>
                            <th className="py-3 px-4">Station ID</th>
                            <th className="py-3 px-4">Coordinates (Lat, Lng)</th>
                            <th className="py-3 px-4">Covered Demand Zones</th>
                            <th className="py-3 px-4">Served EV Intensity</th>
                            <th className="py-3 px-4">Avg EV Distance</th>
                            <th className="py-3 px-4">Capital Cost</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800/60">
                          {psoResult.stations.map((st, i) => (
                            <tr key={st.id} className="hover:bg-slate-800/40 transition">
                              <td className="py-3 px-4 font-bold text-emerald-400">
                                S{i + 1} ({st.id})
                              </td>
                              <td className="py-3 px-4 font-mono text-slate-300">
                                {st.lat.toFixed(4)}, {st.lng.toFixed(4)}
                              </td>
                              <td className="py-3 px-4">
                                <span className="px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 font-semibold">
                                  {st.covered_demand_count} zones
                                </span>
                              </td>
                              <td className="py-3 px-4 font-semibold text-white">
                                {st.served_total_weight.toFixed(1)}
                              </td>
                              <td className="py-3 px-4 text-slate-300">
                                {st.avg_distance_to_assigned_demands_km.toFixed(2)} km
                              </td>
                              <td className="py-3 px-4 font-bold text-white">
                                ${st.installation_cost.toLocaleString()}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <div className="p-12 text-center bg-slate-900/50 rounded-xl border border-slate-800">
                      <MapPin className="w-8 h-8 text-slate-600 mx-auto mb-2" />
                      <div className="text-slate-400 text-sm font-medium">No optimized stations placed yet</div>
                      <div className="text-slate-500 text-xs mt-1">
                        Click "Run PSO Optimization" to determine optimal station coordinates.
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
