@echo off
echo Starting Job Alert Full Stack App...

:: Start Backend in a new window (use project's .venv and backend.app)
echo Starting FastAPI Backend on port 8000 using .venv...
start "JobAlert-Backend" cmd /k ".\.venv\Scripts\python -m uvicorn backend.app:app --reload --port 8000"

:: Start Frontend in a new window
echo Starting React Frontend on port 3000...
cd frontend
start "JobAlert-Frontend" cmd /k "npm run dev -- --port 3000"

echo.
echo ========================================
echo App is starting!
echo Backend: http://127.0.0.1:8000
echo Frontend: http://localhost:3000
echo ========================================
timeout /t 5
start http://localhost:3000
