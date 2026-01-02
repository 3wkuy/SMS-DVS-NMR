@echo off
REM ============================================
REM CPMG NMR Analysis Package - Windows Installer
REM ============================================

echo.
echo ============================================
echo CPMG NMR Data Processing Package Installer
echo ============================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.7 or higher from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
)

echo [1/6] Python found:
python --version
echo.

REM Check Python version
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo Python version: %PYTHON_VERSION%
echo.

REM Check if pip is available
pip --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: pip is not available
    echo Python is installed but pip is missing. This is unusual.
    echo Please reinstall Python or ensure pip is included.
    pause
    exit /b 1
)

echo [2/6] pip found:
pip --version
echo.

REM Upgrade pip
echo [3/6] Upgrading pip...
python -m pip install --upgrade pip
if %errorlevel% neq 0 (
    echo WARNING: Failed to upgrade pip, continuing anyway...
)
echo.

REM Install dependencies
echo [4/6] Installing required packages...
pip install numpy matplotlib scipy pandas
if %errorlevel% neq 0 (
    echo ERROR: Failed to install required packages
    echo Please check your internet connection and try again
    pause
    exit /b 1
)
echo.

REM Install pywin32 for Windows
echo [5/6] Installing pywin32 for Excel integration...
pip install pywin32
if %errorlevel% neq 0 (
    echo WARNING: pywin32 installation failed
    echo Excel integration may not work, but basic functionality is still available
    echo You can install it later with: pip install pywin32
) else (
    echo Running pywin32 post-install script...
    python Scripts/pywin32_postinstall.py -install >nul 2>&1
)
echo.

REM Verify installations
echo [6/6] Verifying installations...
echo.
python -c "import numpy; print('  numpy:', numpy.__version__)"
python -c "import matplotlib; print('  matplotlib:', matplotlib.__version__)"
python -c "import scipy; print('  scipy:', scipy.__version__)"
python -c "import pandas; print('  pandas:', pandas.__version__)"
python -c "import sys; print('  Python:', sys.version.split()[0])"
echo.

REM Check for pywin32
python -c "import win32com.client; print('  pywin32: Installed')" 2>nul
if %errorlevel% neq 0 (
    echo   pywin32: Not installed (optional)
)
echo.

echo ============================================
echo Installation completed successfully!
echo ============================================
echo.
echo You can now run the analysis with:
echo   python run_nmr_analysis.py
echo.
echo For more information, see README.md
echo.

REM Ask if user wants to run the analysis now
set /p RUN_NOW="Do you want to run the analysis now? (y/n): "
if /i "%RUN_NOW%"=="y" (
    echo.
    echo Starting CPMG NMR Analysis...
    echo.
    python run_nmr_analysis.py
) else (
    echo.
    echo You can run the analysis later with:
    echo   python run_nmr_analysis.py
    echo.
)

pause

