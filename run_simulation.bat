@echo off
REM ============================================================================
REM Smart Grid Simulation with Enhanced Anomaly Detection
REM ============================================================================

echo.
echo ================================================================================
echo    SMART GRID SIMULATION WITH ENHANCED ANOMALY DETECTION
echo ================================================================================
echo.

REM Check if Python 3.10 64-bit is available
py -3.10-64 --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python 3.10 64-bit not found!
    echo.
    echo Please install Python 3.10 64-bit from:
    echo https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

echo [INFO] Python 3.10 64-bit found
echo.

REM Check if dependencies are installed
echo [INFO] Checking dependencies...
py -3.10-64 -c "import torch; import pandas; import numpy; import sklearn" >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Some dependencies are missing
    echo [INFO] Installing dependencies...
    py -3.10-64 -m pip install -r ml_pipeline\requirements_ml.txt
    if errorlevel 1 (
        echo [ERROR] Failed to install dependencies
        pause
        exit /b 1
    )
)

echo [INFO] All dependencies installed
echo.

REM Run the simulation
echo ================================================================================
echo    STARTING SIMULATION
echo ================================================================================
echo.

py -3.10-64 run_simulation_with_enhanced_detection.py

if errorlevel 1 (
    echo.
    echo [ERROR] Simulation failed!
    pause
    exit /b 1
)

echo.
echo ================================================================================
echo    SIMULATION COMPLETE
echo ================================================================================
echo.
echo Results saved to: simulation_results\
echo.
echo Open the following files to view results:
echo   - simulation_results\simulation_summary.txt
echo   - simulation_results\simulation_results.csv
echo   - simulation_results\plots\
echo.

pause
