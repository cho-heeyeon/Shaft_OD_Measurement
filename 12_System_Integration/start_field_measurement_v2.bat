@echo off
cd /d "%~dp0"

echo ==========================================
echo Shaft OD Field Measurement System V2
echo ==========================================

echo [1/3] Starting FastAPI...
start "Shaft OD - FastAPI" cmd /k python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000

timeout /t 3 /nobreak > nul

echo [2/3] Starting Streamlit V2...
start "Shaft OD - Streamlit V2" cmd /k python -m streamlit run frontend\streamlit_app_mobile_v2.py --server.address 0.0.0.0 --server.port 8501

timeout /t 3 /nobreak > nul

echo [3/3] Starting ngrok HTTPS...
start "Shaft OD - ngrok" cmd /k ngrok http 8501

echo.
echo ==========================================
echo FastAPI   : http://localhost:8000
echo Streamlit : http://localhost:8501
echo Mobile    : Check HTTPS Forwarding address
echo             in the ngrok window.
echo ==========================================
echo.
echo Keep all three windows open while measuring.
pause
