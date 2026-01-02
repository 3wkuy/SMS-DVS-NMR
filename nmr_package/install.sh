#!/bin/bash

# ============================================
# CPMG NMR Analysis Package - Linux/Mac Installer
# ============================================

echo ""
echo "============================================"
echo "CPMG NMR Data Processing Package Installer"
echo "============================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed or not in PATH"
    echo "Please install Python 3.7 or higher"
    echo ""
    echo "On Ubuntu/Debian: sudo apt-get install python3 python3-pip"
    echo "On Fedora: sudo dnf install python3 python3-pip"
    echo "On macOS: brew install python3"
    exit 1
fi

echo "[1/6] Python found:"
python3 --version
echo ""

# Check if pip is available
if ! command -v pip3 &> /dev/null; then
    echo "ERROR: pip3 is not available"
    echo "Please install pip3"
    echo ""
    echo "On Ubuntu/Debian: sudo apt-get install python3-pip"
    echo "On macOS: pip3 should come with Python3"
    exit 1
fi

echo "[2/6] pip3 found:"
pip3 --version
echo ""

# Upgrade pip
echo "[3/6] Upgrading pip..."
pip3 install --upgrade pip || {
    echo "WARNING: Failed to upgrade pip, continuing anyway..."
}
echo ""

# Install dependencies
echo "[4/6] Installing required packages..."
pip3 install numpy matplotlib scipy pandas || {
    echo "ERROR: Failed to install required packages"
    echo "Please check your internet connection and try again"
    exit 1
}
echo ""

# Verify installations
echo "[5/6] Verifying installations..."
echo ""
python3 -c "import numpy; print('  numpy:', numpy.__version__)" || { echo "ERROR: numpy not found"; exit 1; }
python3 -c "import matplotlib; print('  matplotlib:', matplotlib.__version__)" || { echo "ERROR: matplotlib not found"; exit 1; }
python3 -c "import scipy; print('  scipy:', scipy.__version__)" || { echo "ERROR: scipy not found"; exit 1; }
python3 -c "import pandas; print('  pandas:', pandas.__version__)" || { echo "ERROR: pandas not found"; exit 1; }
python3 -c "import sys; print('  Python:', sys.version.split()[0])"
echo ""

# Check for win32com (not available on Linux/Mac)
echo "Note: pywin32 is not required on Linux/Mac systems"
echo ""

# Success message
echo "[6/6] Installation completed!"
echo ""
echo "============================================"
echo "Installation completed successfully!"
echo "============================================"
echo ""
echo "You can now run the analysis with:"
echo "  python3 run_nmr_analysis.py"
echo ""
echo "For more information, see README.md"
echo ""

# Ask if user wants to run the analysis now
read -p "Do you want to run the analysis now? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "Starting CPMG NMR Analysis..."
    echo ""
    python3 run_nmr_analysis.py
else
    echo ""
    echo "You can run the analysis later with:"
    echo "  python3 run_nmr_analysis.py"
    echo ""
fi

