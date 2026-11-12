# ⚡ EV Charging Station Placement Optimization using Particle Swarm Optimization (PSO)

An end-to-end multi-objective optimization system for electric vehicle (EV) charging station placement in urban corridors. Combines a Python/FastAPI backend powered by vectorized Particle Swarm Optimization (PSO) with an interactive React + Leaflet GIS dashboard.

---

## 🚀 Key Features

- **Multi-Objective PSO Algorithm**: Optimizes charging station locations simultaneously balancing:
  - **Demand Coverage**: Maximizes EV population within service radius $R$.
  - **Travel Distance**: Minimizes average distance between EVs and nearest stations.
  - **Capital & Grid Infrastructure Cost**: Minimizes substation trenching and connection costs based on distance to high-voltage grid nodes.
  - **Polygon Boundary Feasibility**: Ray-casting boundary enforcement keeping stations within municipal service zones.
- **Baseline Comparison Engine**: Benchmarks PSO solutions directly against random placement across coverage gain, travel distance reduction, and capital savings.
- **Interactive GIS Map**: Real-time Leaflet visualization showing city polygons, power grid substations, demand clusters, stations, and coverage radii.
- **Convergence Trajectory Analytics**: Live Recharts tracking fitness minimization and coverage gains across epochs.
- **Preconfigured Urban Scenarios**:
  - **Austin Metropolitan Area (Texas EV Corridor)**: 50 demand nodes, high-growth tech corridor.
  - **San Francisco Peninsula**: Dense coastal grid with elevation and boundary constraints.

---

## 📊 Performance Comparison (Austin Scenario Sample)

| Metric | Random Baseline | PSO Optimized | Improvement |
| :--- | :--- | :--- | :--- |
| **Demand Coverage** | 20.8% | **78.1%** | **+57.3%** |
| **Average Travel Distance** | 5.49 km | **3.32 km** | **+39.5% reduction** |
| **Total Capital Cost** | \$495,971.26 | **\$455,329.68** | **-8.2% savings** |
| **Objective Fitness Score** | 0.50635 | **0.24319** | **+52.0%** |
| **Execution Time** | — | **~1.2 seconds** | 50 iterations |

---

## 🛠️ Tech Stack

- **Backend**: Python 3.11+, FastAPI, Uvicorn, NumPy, Pydantic v2, Pytest
- **Frontend**: React 19, TypeScript, Vite, Tailwind CSS, Leaflet, Recharts, Lucide Icons
- **Optimization**: Particle Swarm Optimization (PSO) with adaptive inertia weight decay ($w_{\text{max}} \to w_{\text{min}}$) and social/cognitive acceleration ($c_1, c_2$)

---

## 🏁 Quickstart

### 1. One-Click Launch (Windows)
Double-click `start_all.bat` or run:
```cmd
.\start_all.bat
```
This automatically starts both the FastAPI backend (`http://127.0.0.1:8000`) and the Vite frontend (`http://127.0.0.1:5173/`).

---

### 2. Manual Setup

#### Backend Setup
```bash
cd backend
pip install -r requirements.txt

# Run CLI Optimization Demo
python ../run.py

# Start Backend Server
python ../run.py --serve --port 8000
```
- API Docs: `http://127.0.0.1:8000/docs`
- Health Check: `http://127.0.0.1:8000/api/health`

#### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
Open `http://127.0.0.1:5173/` in your browser.

#### Running Tests
```bash
pytest backend/tests/test_pso.py
```

---

## 📡 API Endpoints

- `GET /api/scenarios`: List available city scenarios.
- `GET /api/scenario-data?scenario_id=...`: Retrieve boundaries, demand points, and grid nodes.
- `POST /api/optimize`: Run PSO optimization with customizable hyperparameters.
- `POST /api/baseline`: Run random baseline placement.
- `POST /api/compare`: Run both and return side-by-side comparative metrics.

---

## 📄 License
MIT License
