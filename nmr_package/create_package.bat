@echo off
REM ============================================
REM Package Creation Script
REM This script helps organize all the files
REM into the proper package structure
REM ============================================

echo.
echo ============================================
REM Creating CPMG NMR Analysis Package
REM ============================================
echo.

REM Create directory structure
echo Creating directory structure...
mkdir nmr_cpmg_analysis 2>nul
mkdir examples 2>nul
mkdir ILT_Results 2>nul

echo Checking required files...

REM Check if main files exist
if exist "nmr_cpmg_analysis\__init__.py" (
    echo [OK] nmr_cpmg_analysis\__init__.py
) else (
    echo [MISSING] nmr_cpmg_analysis\__init__.py
)

if exist "nmr_cpmg_analysis\merged_CPMG_ILT_analysis_v1_3.py" (
    echo [OK] nmr_cpmg_analysis\merged_CPMG_ILT_analysis_v1_3.py
) else (
    echo [MISSING] nmr_cpmg_analysis\merged_CPMG_ILT_analysis_v1_3.py
)

if exist "requirements.txt" (
    echo [OK] requirements.txt
) else (
    echo [MISSING] requirements.txt
)

if exist "install.bat" (
    echo [OK] install.bat
) else (
    echo [MISSING] install.bat
)

if exist "run_nmr_analysis.py" (
    echo [OK] run_nmr_analysis.py
) else (
    echo [MISSING] run_nmr_analysis.py
)

if exist "README.md" (
    echo [OK] README.md
) else (
    echo [MISSING] README.md
)

echo.
echo ============================================
REM Package structure check complete!
REM ============================================
echo.
echo Next steps:
echo 1. Review INSTRUCTIONS.txt for detailed setup
echo 2. Run install.bat to install dependencies
echo 3. Run python run_nmr_analysis.py to start
echo.
echo For more help, see:
echo   - README.md (main documentation)
echo   - USER_GUIDE.md (detailed guide)
echo   - QUICKSTART.md (quick start)
echo.
pause

