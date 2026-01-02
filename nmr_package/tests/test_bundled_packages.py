#!/usr/bin/env python3
"""
Test script for bundled external packages
Verifies that ITAMeD and other external packages are working correctly
"""

import sys
import os
from pathlib import Path

# Add package to path
current_dir = Path(__file__).parent.parent
sys.path.insert(0, str(current_dir))

print("="*70)
print("Testing Bundled External Packages")
print("="*70)
print()

# Test 1: Check external_packages directory
print("Test 1: Check external_packages Directory")
print("-"*70)
external_dir = current_dir / "external_packages"
print(f"Looking for: {external_dir}")
print(f"Exists: {external_dir.exists()}")

if external_dir.exists():
    print("✓ external_packages directory found")
    
    # Check for ITAMeD
    processing_dir = external_dir / "processing"
    if processing_dir.exists():
        print("  ✓ processing/ directory found")
        core_file = processing_dir / "core.py"
        if core_file.exists():
            print("  ✓ processing/core.py found")
        else:
            print("  ✗ processing/core.py not found")
    else:
        print("  ✗ processing/ directory not found")
    
    # Check for ITAMeD L2
    l2_file = external_dir / "itamed_l2_version.py"
    if l2_file.exists():
        print("  ✓ itamed_l2_version.py found")
    else:
        print("  ✗ itamed_l2_version.py not found")
else:
    print("✗ external_packages directory not found")
print()

# Test 2: Import external_packages module
print("Test 2: Import external_packages Module")
print("-"*70)
try:
    from external_packages import (
        processing,
        itamed_l2_version,
        ITAMED_AVAILABLE,
        ITAMED_L2_AVAILABLE,
    )
    print("✓ external_packages module imported successfully")
    print(f"  ITAMED_AVAILABLE: {ITAMED_AVAILABLE}")
    print(f"  ITAMED_L2_AVAILABLE: {ITAMED_L2_AVAILABLE}")
except ImportError as e:
    print(f"✗ Failed to import external_packages: {e}")
    print("  This is expected if external_packages are not included yet")
print()

# Test 3: Import ITAMeD processing
print("Test 3: Import ITAMeD Processing")
print("-"*70)
try:
    from external_packages import processing
    print("✓ ITAMeD processing imported")
    
    # Try to access itamed1d
    try:
        if hasattr(processing, 'core'):
            from external_packages.processing import core
            if hasattr(core, 'itamed1d'):
                print("  ✓ itamed1d function found in core module")
            else:
                print("  ✗ itamed1d function NOT found in core module")
        elif hasattr(processing, 'itamed1d'):
            print("  ✓ itamed1d function found directly")
        else:
            print("  ✗ itamed1d function NOT found")
    except Exception as e:
        print(f"  ✗ Error accessing itamed1d: {e}")
except ImportError as e:
    print(f"✗ Failed to import ITAMeD processing: {e}")
    print("  This is expected if ITAMeD is not bundled")
print()

# Test 4: Import ITAMeD L2
print("Test 4: Import ITAMeD L2")
print("-"*70)
try:
    from external_packages import itamed_l2_version
    print("✓ ITAMeD L2 imported")
    
    if hasattr(itamed_l2_version, 'itamed1d_l2'):
        print("  ✓ itamed1d_l2 function found")
    else:
        print("  ✗ itamed1d_l2 function NOT found")
except ImportError as e:
    print(f"✗ Failed to import ITAmeD L2: {e}")
    print("  This is expected if ITAmeD L2 is not bundled")
print()

# Test 5: Check main analysis module
print("Test 5: Check Main Analysis Module")
print("-"*70)
try:
    from nmr_cpmg_analysis import (
        perform_ilt,
        rmea1d,
        find_optimal_lambda,
        main,
        ITAMED_BUNDLED,
    )
    print("✓ Main analysis module imported successfully")
    print(f"  perform_ilt: {perform_ilt is not None}")
    print(f"  rmea1d: {rmea1d is not None}")
    print(f"  find_optimal_lambda: {find_optimal_lambda is not None}")
    print(f"  main: {main is not None}")
    print(f"  ITAMED_BUNDLED: {ITAMED_BUNDLED}")
except ImportError as e:
    print(f"✗ Failed to import main analysis: {e}")
print()

# Test 6: Summary
print("="*70)
print("SUMMARY")
print("="*70)
print()

# Check external packages status
external_packages_exist = external_dir.exists()
print(f"External Packages Directory: {'✓ EXISTS' if external_packages_exist else '✗ NOT FOUND'}")

if external_packages_exist:
    itamed_found = (external_dir / "processing").exists()
    itamed_l2_found = (external_dir / "itamed_l2_version.py").exists()
    
    print(f"ITAMeD Processing: {'✓ FOUND' if itamed_found else '✗ NOT FOUND'}")
    print(f"ITAMeD L2: {'✓ FOUND' if itamed_l2_found else '✗ NOT FOUND'}")
else:
    print("ITAMeD: Not bundled (RMEA1D will be used)")

print()

# Recommendations
print("RECOMMENDATIONS:")
print("-"*70)

if external_packages_exist:
    print("✓ External packages are bundled")
    print("  Users can use ITAmeD without external installation")
else:
    print("⚠ External packages are NOT bundled")
    print("  Users will need to install ITAmeD separately if they want it")
    print("  RMEA1D (built-in) will work fine without ITAmeD")

print()
print("="*70)
print("Test Complete")
print("="*70)
print()

# Instructions for including packages
if not external_packages_exist:
    print("TO INCLUDE EXTERNAL PACKAGES:")
    print("-"*70)
    print("1. Read: BUNDLE_EXTERNAL_PACKAGES.md")
    print("2. Create: external_packages/ directory")
    print("3. Copy ITAMeD source code to external_packages/")
    print("4. Create: external_packages/__init__.py")
    print("5. Update main analysis code imports")
    print("6. Run this test again to verify")
    print()

