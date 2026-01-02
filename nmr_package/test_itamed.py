#!/usr/bin/env python3
"""
Test script to verify ITAMeD installation
This script checks if ITAMeD and ITAMeD L2 are available
"""

import sys
import subprocess
from pathlib import Path

print("="*70)
print("ITAMeD Installation Test Script")
print("="*70)
print()

# Test 1: Check Python version
print("Test 1: Python Version")
print("-"*70)
python_version = sys.version_info
print(f"Python version: {python_version.major}.{python_version.minor}.{python_version.micro}")
if python_version >= (3, 7):
    print("✓ Python 3.7+ detected - Good!")
else:
    print("✗ Python version is too old - Requires 3.7 or higher")
print()

# Test 2: Check ITAMeD location
print("Test 2: ITAMeD Location")
print("-"*70)
ITAMED_REPO = Path.home() / "ITAMeD_python"
print(f"Expected location: {ITAMED_REPO}")
print(f"Directory exists: {ITAMED_REPO.exists()}")

if ITAMED_REPO.exists():
    print("✓ ITAMeD_python directory found")
    # Check structure
    processing_dir = ITAMED_REPO / "processing"
    if processing_dir.exists():
        print("  ✓ processing/ directory found")
        core_file = processing_dir / "core.py"
        if core_file.exists():
            print("  ✓ processing/core.py found")
        else:
            print("  ✗ processing/core.py not found")
    else:
        print("  ✗ processing/ directory not found")
else:
    print("✗ ITAMeD_python directory not found")
    print("  Download ITAMeD_python and extract to your home directory:")
    print(f"    Expected: {ITAMED_REPO}")
print()

# Test 3: Try to import ITAMeD
print("Test 3: Import ITAMeD")
print("-"*70)
itamed_available = False
itamed_version = None

try:
    # Add ITAMeD_python to path if it exists
    if ITAMED_REPO.exists():
        itamed_path = str(ITAMED_REPO)
        if itamed_path not in sys.path:
            sys.path.insert(0, itamed_path)
            print(f"Added to Python path: {itamed_path}")

    # Try to import
    import processing.core as itamed
    print("✓ Successfully imported ITAMeD module")
    itamed_available = True

    # Check for functions
    if hasattr(itamed, 'itamed1d'):
        print("  ✓ itamed1d function found")
    else:
        print("  ✗ itamed1d function NOT found")

    # Try to get version (if available)
    try:
        itamed_version = getattr(itamed, '__version__', 'unknown')
        print(f"  Version: {itamed_version}")
    except:
        pass

except ImportError as e:
    print(f"✗ Failed to import ITAMeD: {e}")
    print("  This is expected if ITAMeD is not installed")
except Exception as e:
    print(f"✗ Error importing ITAMeD: {e}")
print()

# Test 4: Try to import ITAMeD L2
print("Test 4: Import ITAMeD L2 (Optional)")
print("-"*70)
itamed_l2_available = False

try:
    # First try simple import
    import itamed_l2_version as itamed_l2
    print("✓ Successfully imported ITAMeD L2 version")

    if hasattr(itamed_l2, 'itamed1d_l2'):
        print("  ✓ itamed1d_l2 function found")
        itamed_l2_available = True
    else:
        print("  ✗ itamed1d_l2 function NOT found")

except ImportError as e:
    print(f"✗ Failed to import ITAMeD L2: {e}")
    print("  This is expected - L2 version is optional")

    # Try loading from script directory
    try:
        script_dir = Path(__file__).parent
        l2_module_path = script_dir / "itamed_l2_version.py"
        if l2_module_path.exists():
            print(f"  Found itamed_l2_version.py at: {l2_module_path}")
            import importlib.util
            spec = importlib.util.spec_from_file_location("itamed_l2_version", l2_module_path)
            itamed_l2 = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(itamed_l2)

            if hasattr(itamed_l2, 'itamed1d_l2'):
                print("  ✓ Successfully loaded ITAMeD L2 from script directory")
                itamed_l2_available = True
            else:
                print("  ✗ Loaded module but itamed1d_l2 not found")
        else:
            print(f"  ✗ itamed_l2_version.py not found in script directory")
    except Exception as e2:
        print(f"  ✗ Error loading L2 from script directory: {e2}")
print()

# Test 5: Check if ITAMeD L2 is in ITAMeD_python
print("Test 5: Check for itamed_l2_version.py in ITAMeD_python")
print("-"*70)
if ITAMED_REPO.exists():
    l2_file = ITAMED_REPO / "itamed_l2_version.py"
    if l2_file.exists():
        print("✓ itamed_l2_version.py found in ITAMeD_python directory")
    else:
        print("✗ itamed_l2_version.py not found in ITAMeD_python directory")
        print("  This file is optional - L2 regularization requires it")
else:
    print("✗ ITAMeD_python directory not found")
print()

# Test 6: Summary
print("="*70)
print("SUMMARY")
print("="*70)

print()
print("Package Status:")
print(f"  ITAMeD:         {'✓ AVAILABLE' if itamed_available else '✗ NOT AVAILABLE'}")
print(f"  ITAMeD L2:      {'✓ AVAILABLE' if itamed_l2_available else '✗ NOT AVAILABLE'}")
print()

if itamed_available:
    print("Recommendation:")
    print("  ✓ You can use both RMEA1D and ITAMeD methods")
    if itamed_l2_available:
        print("  ✓ L2 regularization is available for smooth peaks")
        print("  ✓ L1 regularization is available for sparse peaks")
    else:
        print("  ⚠ L2 regularization not available (optional)")
        print("  ✓ L1 regularization is available")
    print()
    print("Usage:")
    print("  method='rmea1d'  → Built-in RMEA1D method (fast)")
    print("  method='itamed'   → ITAMeD method (advanced)")
else:
    print("Recommendation:")
    print("  ✓ Use RMEA1D method (built-in, always available)")
    print("  ⚠ ITAMeD is not installed")
    print("  ⚠ To use ITAMeD, see ITAMED_INSTALLATION.md")
    print()
    print("Usage:")
    print("  method='rmea1d'  → Built-in RMEA1D method (works fine)")
    print("  method='itamed'   → NOT AVAILABLE")

print()
print("="*70)
print("Test Complete")
print("="*70)
print()
print("For ITAMeD installation instructions, see: ITAMED_INSTALLATION.md")
print()

# Suggest next steps
if not itamed_available:
    print("Next Steps:")
    print("  1. Continue using RMEA1D method (works great!)")
    print("  2. OR install ITAMeD if you need advanced features:")
    print("     a. Download ITAMeD_python from GitHub")
    print(f"     b. Extract to: {ITAMED_REPO}")
    print("     c. Run this test script again to verify")
else:
    print("Next Steps:")
    print("  1. Use either RMEA1D or ITAMeD in your analysis")
    print("  2. See examples/simple_example.py for code examples")
    print("  3. Run: python run_nmr_analysis.py to start analysis")

print()

