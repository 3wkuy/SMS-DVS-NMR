#!/usr/bin/env python3
"""
Check if ITAmED is already installed on your computer
This script helps you locate ITAmED files for bundling
"""

import sys
import os
from pathlib import Path

print("="*70)
print("Checking for ITAmED on Your Computer")
print("="*70)
print()

# Check 1: Look in home directory
print("Check 1: ITAmED_python in Home Directory")
print("-"*70)
home_dir = Path.home()
itamed_home = home_dir / "ITAMED_python"

print(f"Looking for: {itamed_home}")
print(f"Exists: {itamed_home.exists()}")

if itamed_home.exists():
    print("✓ ITAmED_python directory found in home directory!")
    print()
    
    # Check for processing directory
    processing_dir = itamed_home / "processing"
    if processing_dir.exists():
        print("  ✓ processing/ directory found")
        
        # Check for files
        init_file = processing_dir / "__init__.py"
        core_file = processing_dir / "core.py"
        
        print(f"    {init_file.name}: {'✓ EXISTS' if init_file.exists() else '✗ NOT FOUND'}")
        print(f"    {core_file.name}: {'✓ EXISTS' if core_file.exists() else '✗ NOT FOUND'}")
        
        if init_file.exists() and core_file.exists():
            print("  ✓ ITAmED processing module is complete")
        else:
            print("  ✗ ITAmED processing module is incomplete")
    else:
        print("  ✗ processing/ directory NOT found")
    
    # Check for L2 version
    l2_file = itamed_home / "itamed_l2_version.py"
    print(f"    {l2_file.name}: {'✓ EXISTS' if l2_file.exists() else '✗ NOT FOUND'}")
    
    if l2_file.exists():
        print("  ✓ ITAmED L2 version is available")
    else:
        print("  ✗ ITAmED L2 version NOT found (optional)")
    
    print()
    print("📁 ITAmED files found:")
    print(f"  Source: {itamed_home}")
    print(f"  Copy these files to: nmr_package/external_packages/")
    print()
else:
    print("✗ ITAmED_python directory NOT found in home directory")
    print()
    print("This is expected if you haven't installed ITAmED before.")
    print()

print()

# Check 2: Try to import ITAmED
print("Check 2: Try to Import ITAmED")
print("-"*70)
itamed_imported = False
itamed_l2_imported = False

try:
    # Try importing from home directory
    if itamed_home.exists():
        itamed_path = str(itamed_home)
        if itamed_path not in sys.path:
            sys.path.insert(0, itamed_path)
        
        import processing.core as itamed
        print("✓ Successfully imported ITAmED processing.core")
        itamed_imported = True
        
        # Check for functions
        if hasattr(itamed, 'itamed1d'):
            print("  ✓ itamed1d function available")
        else:
            print("  ✗ itamed1d function NOT available")
            
    else:
        print("✗ Cannot import - ITAmED_python directory not found")
        
except ImportError as e:
    print(f"✗ Failed to import ITAmED: {e}")
except Exception as e:
    print(f"✗ Error importing ITAmED: {e}")

print()

try:
    # Try importing L2 version
    if itamed_home.exists():
        l2_file = itamed_home / "itamed_l2_version.py"
        if l2_file.exists():
            import itamed_l2_version
            print("✓ Successfully imported ITAmED L2 version")
            itamed_l2_imported = True
            
            if hasattr(itamed_l2_version, 'itamed1d_l2'):
                print("  ✓ itamed1d_l2 function available")
            else:
                print("  ✗ itamed1d_l2 function NOT available")
        else:
            print("✗ Cannot import - itamed_l2_version.py not found")
    else:
        print("✗ Cannot import - ITAmED_python directory not found")
        
except ImportError as e:
    print(f"✗ Failed to import ITAmED L2: {e}")
except Exception as e:
    print(f"✗ Error importing ITAmED L2: {e}")

print()

# Check 3: List all ITAmED files found
print("Check 3: List All ITAmED Files")
print("-"*70)

if itamed_home.exists():
    print(f"Directory: {itamed_home}")
    print()
    
    # List all Python files
    py_files = list(itamed_home.rglob("*.py"))
    if py_files:
        print(f"Found {len(py_files)} Python file(s):")
        for py_file in sorted(py_files):
            print(f"  {py_file.name}")
    
    # List all directories
    dirs = [d for d in itamed_home.iterdir() if d.is_dir()]
    if dirs:
        print()
        print(f"Found {len(dirs)} directories:")
        for d in sorted(dirs):
            print(f"  {d.name}/")
            
            # List contents
            if d.name == "processing":
                proc_dir = itamed_home / "processing"
                proc_files = list(proc_dir.glob("*"))
                print(f"    Contains {len(proc_files)} file(s):")
                for pf in sorted(proc_files):
                    print(f"      {pf.name}")
    print()
else:
    print("✗ ITAmED_python directory not found")

print()

# Check 4: Summary and Recommendations
print("="*70)
print("SUMMARY")
print("="*70)
print()

print("ITAmED Status:")
print(f"  Directory found: {itamed_home.exists()}")
print(f"  Processing module: {'✓ YES' if itamed_imported else '✗ NO'}")
print(f"  L2 version: {'✓ YES' if itamed_l2_imported else '✗ NO'}")
print()

if itamed_home.exists():
    print("✓ ITAmED is installed on your computer!")
    print()
    print("📋 Files to copy to nmr_package/external_packages/:")
    print()
    
    # Files you need
    processing_dir = itamed_home / "processing"
    if processing_dir.exists():
        init_file = processing_dir / "__init__.py"
        core_file = processing_dir / "core.py"
        
        if init_file.exists():
            print("  1. Copy: processing/__init__.py")
            print(f"     From: {init_file}")
            print(f"     To:   nmr_package/external_packages/processing/__init__.py")
        
        if core_file.exists():
            print("  2. Copy: processing/core.py")
            print(f"     From: {core_file}")
            print(f"     To:   nmr_package/external_packages/processing/core.py")
    
    l2_file = itamed_home / "itamed_l2_version.py"
    if l2_file.exists():
        print("  3. Copy: itamed_l2_version.py")
        print(f"     From: {l2_file}")
        print(f"     To:   nmr_package/external_packages/itamed_l2_version.py")
    
    print()
    print("✅ You have the ITAmED files needed for bundling!")
    print()
    print("Next steps:")
    print("  1. Create external_packages/processing/ directory in nmr_package/")
    print("  2. Copy the files listed above")
    print("  3. Run: python tests/test_bundled_packages.py")
    print("  4. Update nmr_cpmg_analysis/merged_CPMG_ILT_analysis_v1_3.py (see BUNDLE_EXTERNAL_PACKAGES.md)")
    
else:
    print("✗ ITAmED is NOT installed on your computer")
    print()
    print("Next steps:")
    print("  1. Download ITAmED from GitHub")
    print("  2. Extract ITAmED_python folder")
    print("  3. Copy files to nmr_package/external_packages/")
    print("  4. See BUNDLE_EXTERNAL_PACKAGES.md for complete guide")

print()
print("="*70)
print("Check Complete")
print("="*70)
print()

# Copy-paste ready instructions
print("📋 Copy-Paste Commands (if ITAmED found):")
print("-"*70)
if itamed_home.exists():
    print("# Create directories:")
    print("mkdir -p nmr_package/external_packages/processing")
    print()
    print("# Copy files:")
    processing_dir = itamed_home / "processing"
    
    if (processing_dir / "__init__.py").exists():
        print(f'cp "{itamed_home}/processing/__init__.py" "nmr_package/external_packages/processing/"')
    if (processing_dir / "core.py").exists():
        print(f'cp "{itamed_home}/processing/core.py" "nmr_package/external_packages/processing/"')
    
    if (itamed_home / "itamed_l2_version.py").exists():
        print(f'cp "{itamed_home}/itamed_l2_version.py" "nmr_package/external_packages/"')
    print()
    print("# Or on Windows PowerShell:")
    print("# Create directories:")
    print('New-Item -ItemType Directory -Path "nmr_package\\external_packages\\processing"')
    print()
    print("# Copy files:")
    if (processing_dir / "__init__.py").exists():
        print(f'Copy-Item "{itamed_home}\\processing\\__init__.py" "nmr_package\\external_packages\\processing\\')
    if (processing_dir / "core.py").exists():
        print(f'Copy-Item "{itamed_home}\\processing\\core.py" "nmr_package\\external_packages\\processing\\')
    
    if (itamed_home / "itamed_l2_version.py").exists():
        print(f'Copy-Item "{itamed_home}\\itamed_l2_version.py" "nmr_package\\external_packages\\"')
else:
    print("# ITAmED not found - Download instructions:")
    print("# See BUNDLE_EXTERNAL_PACKAGES.md or GITHUB_UPLOAD_GUIDE.md")

print()

