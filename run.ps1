param(
    [string]$Action = "demo",
    [string]$Scenario = "austin_metro",
    [int]$Stations = 6,
    [double]$Radius = 3.5,
    [int]$SwarmSize = 30,
    [int]$Iterations = 50
)

$PythonPath = "C:\Users\Murugan Durai\AppData\Local\Programs\Python\Python312\python.exe"
if (-not (Test-Path $PythonPath)) {
    $PythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if ($PythonCmd) {
        $PythonPath = $PythonCmd.Source
    } else {
        Write-Error "Python 3.12 executable was not found."
        exit 1
    }
}

if ($Action -eq "serve") {
    Write-Host "Starting FastAPI Backend Server on http://127.0.0.1:8000 ..." -ForegroundColor Cyan
    Write-Host "Interactive API Docs: http://127.0.0.1:8000/docs" -ForegroundColor Green
    & $PythonPath run.py --serve
} elseif ($Action -eq "frontend") {
    Write-Host "Starting Frontend Dev Server on http://localhost:5173 ..." -ForegroundColor Cyan
    $env:PATH = "C:\Program Files\nodejs;" + $env:PATH
    Set-Location frontend
    & "C:\Program Files\nodejs\npm.cmd" run dev
} elseif ($Action -eq "test") {
    Write-Host "Executing PSO Test Suite..." -ForegroundColor Cyan
    & $PythonPath -m pytest backend/tests/test_pso.py
} else {
    & $PythonPath run.py --scenario $Scenario -k $Stations -r $Radius -p $SwarmSize -i $Iterations
}

