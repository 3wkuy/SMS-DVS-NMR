# ITAMeD Installation Guide

## Overview

The CPMG NMR Analysis Package includes two ILT (Inverse Laplace Transform) methods:

1. **RMEA1D** - Built-in, always available, fast and reliable
2. **ITAMeD** - Optional advanced method with L1/L2 regularization

**TL;DR:** You DON'T need ITAMeD for basic usage. RMEA1D works great!
- Use RMEA1D if you're new to NMR analysis
- Use ITAMeD if you need advanced features or better results for specific data

---

## Do You Need ITAMeD?

### Use RMEA1D (Built-in) if:
- ✅ You're new to NMR analysis
- ✅ You have limited computational resources
- ✅ Your data has good signal-to-noise ratio
- ✅ You want fast processing
- ✅ You don't have ITAMeD installed

### Use ITAMeD (Optional) if:
- ✅ You need sparse/sharp peak detection
- ✅ You have data with low signal-to-noise
- ✅ You want to try both L1 and L2 regularization
- ✅ You're working with specific research requirements
- ✅ You have ITAMeD_python installed

**Recommendation:** Start with RMEA1D (default). Try ITAMeD only if you're not satisfied with RMEA1D results.

---

## ITAMeD vs RMEA1D Comparison

| Feature | RMEA1D (Built-in) | ITAMeD (Optional) |
|---------|-------------------|-------------------|
| **Availability** | Always available | Requires installation |
| **Speed** | Fast | Slower (iterative) |
| **Regularization** | Tikhonov (L2) | L1 or L2 (configurable) |
| **Best For** | Most applications | Sparse/sharp peaks |
| **Setup** | No setup needed | Requires installation |
| **Reliability** | Very high | High (if installed) |
| **CPU Usage** | Low | Moderate |

---

## Installing ITAMeD

### Method 1: From GitHub (Recommended)

1. **Clone or download ITAMeD_python:**

   ```bash
   git clone https://github.com/your-repo/ITAMeD_python.git ~/ITAMeD_python
   ```

   Or download and extract to: `~/ITAMeD_python` (Linux/Mac) or `C:\Users\YourName\ITAMeD_python` (Windows)

2. **Verify installation:**

   The package will automatically detect ITAMeD if it's in your home directory.

   When you run the analysis, you should see:
   ```
   ✓ ITAMeD module available
   ✓ ITAMeD L2 version available (for smooth, broad peaks)
   ```

### Method 2: Manual Installation

1. **Download ITAMeD_python package** from GitHub or other source

2. **Extract to your home directory:**

   - **Linux/Mac:** `~/ITAMeD_python/`
   - **Windows:** `C:\Users\YourName\ITAMeD_python\`

3. **Verify structure:**
   ```
   ITAMeD_python/
   ├── processing/
   │   └── core.py
   └── ... other files
   ```

### Method 3: Install from ZIP file

1. Download ITAMeD_python as ZIP
2. Extract to: `~/ITAMeD_python/` (Linux/Mac) or `C:\Users\YourName\ITAMeD_python\` (Windows)
3. The package will automatically find it

---

## Using ITAMeD

### Option 1: Interactive Mode

When you run `python run_nmr_analysis.py`, the package will automatically detect ITAMeD and use it if available.

**With ITAMeD installed:**
```
✓ ITAMeD module available
✓ ITAMeD L2 version available (for smooth, broad peaks)
```

**Without ITAMeD installed:**
```
⚠ ITAMeD module not available - only RMEA1D method will be available
```

### Option 2: Command Line

Specify the method explicitly:

```bash
# Use ITAMeD (if installed)
python run_nmr_analysis.py --method itamed

# Use RMEA1D (default, always available)
python run_nmr_analysis.py --method rmea1d
```

### Option 3: In Python Code

```python
from nmr_cpmg_analysis import perform_ilt

# Use ITAMeD (if installed)
f, mc = perform_ilt(t, m, tau, lambda_value, method='itamed')

# Use RMEA1D (default)
f, mc = perform_ilt(t, m, tau, lambda_value, method='rmea1d')
```

---

## ITAMeD Regularization Types

### L1 Regularization (Sparse)
- **Best for:** Sharp, discrete peaks
- **Characteristics:** Promotes sparsity (few non-zero values)
- **Use when:** You expect a small number of distinct T2 components

```python
# Use L1 regularization
f, mc = perform_ilt(t, m, tau, lambda_value, method='itamed')
# L1 is the default if ITAMeD_L2 is not available
```

### L2 Regularization (Smooth)
- **Best for:** Smooth, broad peaks
- **Characteristics:** Penalizes large coefficients
- **Use when:** You expect continuous T2 distributions (experimental data)

```python
# Use L2 regularization (if ITAMeD L2 is installed)
# The package automatically uses L2 when available
f, mc = perform_ilt(t, m, tau, lambda_value, method='itamed')
```

---

## Verification

### Check if ITAMeD is Available

Run the analysis and look for these messages:

**✓ ITAMeD Available:**
```
✓ ITAMeD module available
✓ ITAMeD L2 version available (for smooth, broad peaks)
    [DEBUG] perform_ilt: Using ITAMeD method (lambda=1.00e-03)
    [DEBUG] perform_ilt: Calling ITAMeD L2 (itamed_l2.itamed1d_l2)
```

**✗ ITAMeD Not Available:**
```
⚠ ITAMeD module not available - only RMEA1D method will be available
    [DEBUG] perform_ilt: Using RMEA1D method (lambda=1.00e-03)
```

### Test ITAMeD Installation

Create a test script:

```python
# test_itamed.py
import sys
from pathlib import Path

# Check if ITAMeD is in home directory
ITAMED_REPO = Path.home() / "ITAMeD_python"
print(f"Looking for ITAMeD at: {ITAMED_REPO}")
print(f"ITAMeD exists: {ITAMED_REPO.exists()}")

# Try to import
try:
    if ITAMED_REPO.exists():
        sys.path.insert(0, str(ITAMED_REPO))
    import processing.core as itamed
    print("✓ ITAMeD module imported successfully")
    print(f"  Has itamed1d function: {hasattr(itamed, 'itamed1d')}")
except ImportError as e:
    print(f"✗ ITAMeD module not found: {e}")

# Try L2 version
try:
    import itamed_l2_version as itamed_l2
    print("✓ ITAMeD L2 version imported successfully")
    print(f"  Has itamed1d_l2 function: {hasattr(itamed_l2, 'itamed1d_l2')}")
except ImportError as e:
    print(f"✗ ITAMeD L2 version not found: {e}")
```

Run with:
```bash
python test_itamed.py
```

---

## Troubleshooting

### Problem: "ITAMeD module not available"

**Cause:** ITAMeD_python not in home directory

**Solution:**
1. Install ITAMeD_python to your home directory:
   - Linux/Mac: `~/ITAMeD_python/`
   - Windows: `C:\Users\YourName\ITAMeD_python\`

2. Verify the folder exists
3. Restart the analysis script

### Problem: "ITAMeD imported but itamed1d function not found"

**Cause:** Wrong or incomplete ITAMeD installation

**Solution:**
1. Ensure ITAMeD_python has correct structure:
   ```
   ITAMeD_python/
   ├── processing/
   │   └── core.py  (should contain itamed1d function)
   ```
2. Re-download or re-clone ITAMeD_python
3. Check GitHub for correct version

### Problem: "ITAMeD L2 version not found"

**Cause:** itamed_l2_version.py not found

**Solution:**
1. This is a separate module for L2 regularization
2. May need to be obtained separately
3. L1 regularization (standard ITAMeD) will still work

**Note:** This is NOT a critical error. RMEA1D works fine without ITAMeD.

### Problem: ITAMeD fails during execution

**Cause:** ITAMeD algorithm encountering issues

**Solution:**
The package automatically falls back to RMEA1D if ITAMeD fails:
```
[ERROR] ITAMeD failed with error: [error message]
[ERROR] Falling back to RMEA1D
```

This is normal behavior and the analysis will continue with RMEA1D.

---

## Performance Considerations

### RMEA1D vs ITAMeD Performance

| Metric | RMEA1D | ITAMeD |
|--------|--------|--------|
| **Processing Time** | ~1 sec/file | ~5-10 sec/file |
| **Memory Usage** | Low | Moderate |
| **CPU Usage** | Low | Moderate |
| **Iterations** | N/A | Configurable (default: 10000) |

### When to Use Each

**Use RMEA1D for:**
- Large batch processing (100+ files)
- Limited computational resources
- Time-sensitive analysis
- Standard NMR data

**Use ITAMeD for:**
- Critical analyses requiring best possible results
- Data with low signal-to-noise
- Sparse/sharp peak detection
- Comparative studies

---

## Configuration

### Change ITAMeD Iterations

In the analysis code (if you want to modify):

```python
# Default iterations: 10000
f, mc = perform_ilt(t, m, tau, lambda_value, method='itamed', niter=10000)

# Faster but less accurate (5000 iterations)
f, mc = perform_ilt(t, m, tau, lambda_value, method='itamed', niter=5000)

# More accurate but slower (20000 iterations)
f, mc = perform_ilt(t, m, tau, lambda_value, method='itamed', niter=20000)
```

### Change Regularization Type

The code defaults to L2 regularization if ITAMeD L2 is available.

To change, edit the code (line 86 of merged_CPMG_ILT_analysis_v1_3.py):

```python
# Use L1 (sparse)
ITAMED_REGULARIZATION = "L1"

# Use L2 (smooth, default)
ITAMED_REGULARIZATION = "L2"
```

---

## Summary

### Key Points:

1. **ITAMeD is OPTIONAL** - RMEA1D works great for most users
2. **ITAMeD requires manual installation** - Not included in this package
3. **RMEA1D is recommended for new users** - Built-in, fast, reliable
4. **ITAMeD provides advanced features** - L1/L2 regularization, sparse detection
5. **Automatic fallback** - ITAMeD failures automatically use RMEA1D

### Installation Checklist:

- [ ] Download ITAMeD_python from GitHub
- [ ] Extract to home directory (~/ITAMeD_python or C:\Users\YourName\ITAMeD_python)
- [ ] Verify installation with test_itamed.py
- [ ] Run analysis - should see "✓ ITAMeD module available"
- [ ] Use method='itamed' in your analysis

### Quick Decision Guide:

```
New to NMR analysis? → Use RMEA1D (built-in)
Need fast processing? → Use RMEA1D (built-in)
Low signal-to-noise? → Try ITAMeD (optional)
Need sparse peaks? → Try ITAMeD (optional)
Comparing methods? → Install ITAMeD (optional)
```

---

## Contact & Support

If you encounter issues with ITAMeD installation:

1. Check ITAMeD_python repository for documentation
2. Verify the folder structure
3. Use the test script (test_itamed.py) to diagnose
4. Fall back to RMEA1D if ITAMeD doesn't work

**Remember:** RMEA1D is a robust, well-tested method that works perfectly without ITAMeD!

---

## Appendix: ITAMeD Directory Structure

### Correct Structure:

```
~/ITAMeD_python/  (Linux/Mac)
C:\Users\YourName\ITAMeD_python\  (Windows)
├── processing/
│   ├── __init__.py
│   └── core.py  ← Contains itamed1d function
├── itamed_l2_version.py  ← Optional, for L2 regularization
└── ... other ITAMeD files
```

### Verification:

Run:
```python
import sys
from pathlib import Path
ITAMED_REPO = Path.home() / "ITAMeD_python"
sys.path.insert(0, str(ITAMED_REPO))
import processing.core as itamed
print(hasattr(itamed, 'itamed1d'))  # Should print: True
```

---

**End of ITAMeD Installation Guide**

For general package usage, see README.md and USER_GUIDE.md.

