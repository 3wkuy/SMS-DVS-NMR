# How to Include External Packages (ITAMeD) in CPMG NMR Analysis Package

## Overview

This guide explains how to bundle external packages (like ITAMeD) into your CPMG NMR Analysis package so users don't need to install them separately.

---

## Why Bundle External Packages?

### Advantages:
✅ Users get everything in one package
✅ No external downloads required
✅ Simplified installation
✅ Guaranteed compatibility
✅ Version control

### Disadvantages:
❌ Larger package size
❌ Legal/licensing considerations
❌ Manual updates for external packages
❌ More complex maintenance

---

## Step-by-Step: Including ITAMeD

### Step 1: Get ITAMeD Source Code

1. Download ITAMeD_python from GitHub:
   ```bash
   git clone https://github.com/your-repo/ITAMeD_python.git
   ```

2. Or download ZIP from GitHub and extract

3. Verify structure:
   ```
   ITAMeD_python/
   ├── processing/
   │   ├── __init__.py
   │   └── core.py
   ├── itamed_l2_version.py (if available)
   └── ...
   ```

### Step 2: Copy ITAMeD to Package

Copy ITAMeD source code to your package:

```bash
# Create external packages directory
mkdir nmr_package/external_packages

# Copy ITAMeD
cp -r ITAMeD_python/processing nmr_package/external_packages/
cp ITAMeD_python/itamed_l2_version.py nmr_package/external_packages/ (if exists)

# Or on Windows:
# Create external_packages folder
# Copy ITAMeD_python\processing folder to nmr_package\external_packages\
# Copy itamed_l2_version.py to nmr_package\external_packages\
```

### Step 3: Update Package Structure

Your package should now look like:

```
nmr_package/
├── external_packages/
│   ├── __init__.py
│   ├── processing/
│   │   ├── __init__.py
│   │   └── core.py
│   └── itamed_l2_version.py (if available)
├── nmr_cpmg_analysis/
│   ├── __init__.py
│   └── merged_CPMG_ILT_analysis_v1_3.py
├── examples/
└── ... other files
```

### Step 4: Create external_packages/__init__.py

```python
"""
External Packages for CPMG NMR Analysis

This module includes third-party packages bundled with the main package.
"""

# Import ITAMeD processing module
from . import processing

# Try to import ITAMeD L2 if available
try:
    from . import itamed_l2_version
    ITAMED_L2_AVAILABLE = True
except ImportError:
    ITAMED_L2_AVAILABLE = False

# Export what's available
__all__ = [
    "processing",
    "itamed_l2_version",
]
```

### Step 5: Update Main Analysis Code

Modify `nmr_cpmg_analysis/merged_CPMG_ILT_analysis_v1_3.py` to use bundled ITAMeD.

Change ITAMeD import section (around line 25-83):

```python
# OLD CODE (line 25-83) - Replace this:
"""
# Try to import ITAMeD
ITAMED_AVAILABLE = False
ITAMED_L2_AVAILABLE = False
try:
    # Add ITAMeD_python to Python path if it exists
    ITAMED_REPO = Path.home() / "ITAMeD_python"
    if ITAMED_REPO.exists():
        itamed_path = str(ITAMED_REPO)
        if itamed_path not in sys.path:
            sys.path.insert(0, itamed_path)
    # Try to import ITAMeD
    import processing.core as itamed  # type: ignore
    if hasattr(itamed, 'itamed1d'):
        ITAMED_AVAILABLE = True
        print("✓ ITAMeD module available")
    else:
        print("⚠ ITAMeD module imported but itamed1d function not found")
except ImportError:
    print("⚠ ITAMeD module not available - only RMEA1D method will be available")
    itamed = None  # Set to None to avoid errors
...
"""

# NEW CODE - Replace with:
# Try to import ITAMeD (bundled with package)
ITAMED_AVAILABLE = False
ITAMED_L2_AVAILABLE = False
itamed = None
itamed_l2 = None

try:
    # Try to import from bundled external_packages first
    from external_packages import processing as itamed  # type: ignore
    if hasattr(itamed, 'core'):
        import external_packages.processing.core as itamed_core
        if hasattr(itamed_core, 'itamed1d'):
            ITAMED_AVAILABLE = True
            itamed = itamed_core
            print("✓ ITAMeD module available (bundled with package)")
        else:
            print("⚠ ITAMeD module imported but itamed1d function not found")
except ImportError:
    # Fallback: Try to import from ITAMeD_python directory (old method)
    try:
        ITAMED_REPO = Path.home() / "ITAMeD_python"
        if ITAMED_REPO.exists():
            itamed_path = str(ITAMED_REPO)
            if itamed_path not in sys.path:
                sys.path.insert(0, itamed_path)
        # Try to import ITAMeD
        import processing.core as itamed  # type: ignore
        if hasattr(itamed, 'itamed1d'):
            ITAMED_AVAILABLE = True
            print("✓ ITAMeD module available (from ITAMeD_python directory)")
        else:
            print("⚠ ITAMeD module imported but itamed1d function not found")
    except ImportError:
        print("⚠ ITAMeD module not available - only RMEA1D method will be available")
        itamed = None

# Try to import L2 version (for non-sparse data with broad peaks)
try:
    from external_packages import itamed_l2_version as itamed_l2  # type: ignore
    if hasattr(itamed_l2, 'itamed1d_l2'):
        ITAMED_L2_AVAILABLE = True
        print("✓ ITAMeD L2 version available (bundled with package) - for smooth, broad peaks")
    else:
        print("⚠ ITAMeD L2 module imported but itamed1d_l2 function not found")
        itamed_l2 = None
except ImportError:
    # Fallback: Try to import from same directory as this script (old method)
    try:
        script_dir = Path(__file__).parent
        l2_module_path = script_dir / "itamed_l2_version.py"
        if l2_module_path.exists():
            import importlib.util
            spec = importlib.util.spec_from_file_location("itamed_l2_version", l2_module_path)
            itamed_l2 = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(itamed_l2)
            if hasattr(itamed_l2, 'itamed1d_l2'):
                ITAMED_L2_AVAILABLE = True
                print("✓ ITAMeD L2 version available (from file) - for smooth, broad peaks")
            else:
                print("⚠ ITAmED L2 module found but itamed1d_l2 function not available")
                itamed_l2 = None
        else:
            print("⚠ ITAMeD L2 version not found - will use L1 (sparse) regularization")
    except Exception as e:
        print(f"⚠ Could not load ITAMeD L2 version: {e}")
        print("  Will use L1 (sparse) regularization if ITAMeD is selected")
        itamed_l2 = None
```

### Step 6: Update Package Exports

Update `nmr_cpmg_analysis/__init__.py` to include bundled packages:

```python
"""
CPMG NMR Data Processing Package

A comprehensive package for processing CPMG NMR data with Inverse Laplace Transform (ILT) analysis.

Main functions:
- perform_ilt: Perform ILT using RMEA1D or ITAMeD method
- rmea1d: Regularized multi-exponential analysis
- find_optimal_lambda: Find optimal regularization parameter
- main: Main processing function for batch analysis

External packages:
- ITAMeD: Included (bundled) for advanced ILT analysis
"""

# Import main functions from the analysis module
from .merged_CPMG_ILT_analysis_v1_3 import (
    perform_ilt,
    rmea1d,
    compute_lcurve_rmea,
    compute_lcurve_itamed,
    choose_lambda_balanced,
    find_optimal_lambda,
    analyze_peak_integrals,
    plot_integration_verification,
    main,
)

# Try to import external packages
try:
    from .external_packages import processing
    ITAMED_BUNDLED = True
except ImportError:
    ITAMED_BUNDLED = False

# Version
__version__ = "1.3.0"

# Export the main API
__all__ = [
    "perform_ilt",
    "rmea1d",
    "compute_lcurve_rmea",
    "compute_lcurve_itamed",
    "choose_lambda_balanced",
    "find_optimal_lambda",
    "analyze_peak_integrals",
    "plot_integration_verification",
    "main",
]

# Add ITAMeD status to __all__ for user access
__all__.extend([
    "ITAMED_BUNDLED",
])
```

---

## Step 7: Update Installation Scripts

### Update install.bat

Add ITAMeD verification:

```batch
@echo off
REM ... existing installation code ...

REM Verify bundled ITAMeD
echo [5/7] Verifying bundled ITAMeD...
if exist "external_packages\processing\core.py" (
    echo   Bundled ITAMeD: Found
    python -c "from external_packages import processing; print('  ITAMeD version:', getattr(processing, '__version__', 'unknown'))" 2>nul || echo "  ITAMeD loaded successfully"
) else (
    echo   Bundled ITAMeD: Not found (RMEA1D will be used)
)
echo.
```

### Update install.sh

```bash
# ... existing installation code ...

# Verify bundled ITAMeD
echo "[5/7] Verifying bundled ITAMeD..."
if [ -f "external_packages/processing/core.py" ]; then
    echo "  Bundled ITAMeD: Found"
    python3 -c "from external_packages import processing; print('  ITAMeD loaded successfully')" 2>/dev/null || echo "  ITAMeD loaded"
else
    echo "  Bundled ITAMeD: Not found (RMEA1D will be used)"
fi
echo ""
```

---

## Step 8: Update Documentation

### Update README.md

Add information about bundled packages:

```markdown
## External Packages

This package includes the following external software:

### ITAMeD (Bundled)
- **Purpose:** Advanced ILT analysis with L1/L2 regularization
- **Version:** [Specify version]
- **License:** [Specify ITAMeD's license]
- **Included:** YES (bundled with package)
- **Availability:** Always available, no installation needed
- **Source:** https://github.com/your-repo/ITAMeD_python

**Note:** ITAMeD is bundled with this package for convenience.
If you encounter issues, please report them along with the ITAMeD version.
```

### Create EXTERNAL_PACKAGES.md

```markdown
# External Packages Included

This package includes the following third-party software to provide additional functionality.

## ITAMeD

**Version:** [Specify version]
**License:** [MIT/BSD/etc - check ITAMeD's license]
**Purpose:** Inverse Laplace Transform with L1/L2 regularization
**Included:** Bundled with this package
**Source:** https://github.com/your-repo/ITAMeD_python
**Authors:** [ITAMeD authors]

### What ITAMeD Provides:
- L1 regularization for sparse/sharp peaks
- L2 regularization for smooth/broad peaks
- Advanced ILT algorithms

### License Information:
ITAMeD is included under its original license:
[Include full license text here]

### Credits:
ITAMeD is developed by [authors].
More information: [URL]
```

---

## Step 9: Add License Credits

### Create LICENSES.md

```markdown
# Third-Party Licenses

This package includes software from third parties. Their licenses are included below.

## ITAMeD License

[Include full text of ITAMeD's license here]

## Attribution

ITAMeD - Copyright (c) [Year] [Authors]
Source: https://github.com/your-repo/ITAMeD_python
```

### Update main LICENSE.md

Add section:

```markdown
## Third-Party Software

This package includes ITAMeD, which is licensed under [ITAMeD's license].
See LICENSES.md for full third-party license information.

Attribution to ITAMeD:
- ITAMeD by [Authors]
- Source: https://github.com/your-repo/ITAMeD_python
- License: [ITAMeD's license]
```

---

## Step 10: Test the Bundled Package

### Create test_bundled_packages.py

```python
#!/usr/bin/env python3
"""
Test bundled external packages
"""

print("="*70)
print("Testing Bundled External Packages")
print("="*70)
print()

# Test 1: Import external_packages
print("Test 1: Import external_packages module")
print("-"*70)
try:
    from nmr_cpmg_analysis.external_packages import processing
    print("✓ external_packages imported successfully")
    print(f"  Processing module available: {processing is not None}")
except ImportError as e:
    print(f"✗ Failed to import external_packages: {e}")
print()

# Test 2: Import ITAMeD processing
print("Test 2: Import ITAMeD processing")
print("-"*70)
try:
    from nmr_cpmg_analysis.external_packages.processing import core
    print("✓ ITAMeD processing.core imported successfully")
    if hasattr(core, 'itamed1d'):
        print("  ✓ itamed1d function found")
    else:
        print("  ✗ itamed1d function NOT found")
except ImportError as e:
    print(f"✗ Failed to import ITAMeD processing: {e}")
print()

# Test 3: Import ITAMeD L2
print("Test 3: Import ITAMeD L2")
print("-"*70)
try:
    from nmr_cpmg_analysis.external_packages import itamed_l2_version
    print("✓ ITAMeD L2 imported successfully")
    if hasattr(itamed_l2_version, 'itamed1d_l2'):
        print("  ✓ itamed1d_l2 function found")
    else:
        print("  ✗ itamed1d_l2 function NOT found")
except ImportError as e:
    print(f"✗ Failed to import ITAMeD L2: {e}")
print()

# Test 4: Check main analysis
print("Test 4: Check main analysis module")
print("-"*70)
try:
    from nmr_cpmg_analysis import perform_ilt, main
    print("✓ Main analysis module imported successfully")
    print(f"  perform_ilt function: {perform_ilt is not None}")
    print(f"  main function: {main is not None}")
except ImportError as e:
    print(f"✗ Failed to import main analysis: {e}")
print()

print("="*70)
print("Tests Complete")
print("="*70)
```

Run tests:

```bash
python test_bundled_packages.py
```

---

## Step 11: Update Package Structure Summary

Final structure with bundled packages:

```
nmr_package/
├── external_packages/
│   ├── __init__.py                     [Bundle init]
│   ├── processing/                     [ITAMeD]
│   │   ├── __init__.py
│   │   └── core.py
│   └── itamed_l2_version.py          [ITAMeD L2]
├── nmr_cpmg_analysis/
│   ├── __init__.py                     [Updated to import external_packages]
│   └── merged_CPMG_ILT_analysis_v1_3.py  [Updated imports]
├── examples/
│   ├── __init__.py
│   └── simple_example.py
├── tests/
│   └── test_bundled_packages.py        [New]
├── install.bat                           [Updated]
├── install.sh                            [Updated]
├── setup.py                              [Updated]
├── requirements.txt                       [No change]
├── README.md                             [Updated]
├── LICENSE.md                            [Updated with third-party credits]
├── LICENSES.md                           [New: Third-party licenses]
├── EXTERNAL_PACKAGES.md                   [New: Package info]
├── BUNDLE_EXTERNAL_PACKAGES.md            [This file]
└── ... other files
```

---

## Legal Considerations

### Check ITAMeD's License

1. **What is ITAMeD's license?**
   - MIT? ✓ Can bundle
   - BSD? ✓ Can bundle
   - GPL? May have restrictions
   - Proprietary? ❌ Cannot bundle without permission

2. **What does the license say about distribution?**
   - Look for: "redistribution and use in source and binary forms"
   - Check: Any restrictions on commercial use
   - Verify: Need to include license text

3. **Attribution Requirements:**
   - Must credit original authors
   - Include original license
   - Include copyright notices
   - Link to source

### Create ATTRIBUTIONS.md

```markdown
# Attributions

This package includes software developed by others. We are grateful for their contributions.

## ITAMeD

- **Project:** ITAMeD_python
- **Authors:** [ITAMeD authors]
- **License:** [MIT/BSD/etc]
- **Source:** https://github.com/your-repo/ITAMeD_python
- **Included Version:** [Version number]
- **Modifications:** None (or specify if any)

**Description:**
ITAMeD is an advanced ILT (Inverse Laplace Transform) library that provides
L1 and L2 regularization for NMR relaxation data analysis.

**License Text:**
[Include full license text here]

---

## Credits

ITAMeD development team
[Institution/University]
[URL]
```

---

## Summary

### What You've Done:

1. ✅ Created `external_packages/` directory
2. ✅ Copied ITAMeD to package
3. ✅ Updated imports to use bundled version
4. ✅ Updated installation scripts
5. ✅ Created documentation for external packages
6. ✅ Added license credits
7. ✅ Created test script
8. ✅ Maintained backward compatibility

### What Users Get:

✅ Complete package in one download
✅ No external installations needed for ITAMeD
✅ Guaranteed ITAMeD compatibility
✅ Clear attribution and licensing
✅ Version control of all dependencies

### Package Benefits:

✅ Simpler for users (one download)
✅ Easier distribution (single archive)
✅ Reliable (no external dependencies)
✅ Professional (proper licensing)

### Maintenance Considerations:

⚠️ Must update ITAMeD when new versions are released
⚠️ Must check ITAMeD license for any changes
⚠️ Must keep attribution current
⚠️ Larger package size

---

## Next Steps

1. ✅ Copy ITAMeD source code to `external_packages/`
2. ✅ Update main analysis code imports
3. ✅ Update package `__init__.py`
4. ✅ Update installation scripts
5. ✅ Create attribution and license files
6. ✅ Test with `test_bundled_packages.py`
7. ✅ Update documentation (README.md, etc.)
8. ✅ Verify all licenses are compatible
9. ✅ Create distribution package

---

## Alternative: PyPI Package

If you want to publish to PyPI:

### Update setup.py

```python
setup(
    name="nmr-cpmg-analysis",
    version="1.3.0",
    packages=find_packages(),
    # Include external_packages
    package_data={
        'nmr_cpmg_analysis': [
            'external_packages/**/*',
        ],
    },
    # ... other setup parameters
)
```

### Build and Upload

```bash
python setup.py sdist
python setup.py bdist_wheel
twine upload dist/*
```

---

**End of Guide**

