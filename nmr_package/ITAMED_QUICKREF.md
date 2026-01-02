# ITAMeD Quick Reference

## TL;DR: Do I Need ITAMeD?

**NO!** For most users, RMEA1D (built-in) works perfectly.

Use ITAMeD ONLY if:
- You need advanced L1/L2 regularization
- You're working with sparse/sharp peaks
- You have low signal-to-noise data
- You want to compare different methods

---

## Quick Decision Tree

```
Start using package
    ↓
New to NMR analysis? → YES → Use RMEA1D (built-in)
                      ↓ NO
Need sparse peak detection? → NO → Use RMEA1D (built-in)
                        ↓ YES
Low signal-to-noise? → YES → Try ITAMeD
                    ↓ NO
Comparing methods? → YES → Install ITAMeD
                 ↓ NO
Time-sensitive? → YES → Use RMEA1D (fast)
             ↓ NO
Any of above? → YES → Install ITAMeD
            ↓ NO
→ Use RMEA1D (built-in)
```

---

## Installation: One Command

```bash
# Download and extract ITAMeD_python to your home directory
# Linux/Mac: ~/ITAMeD_python/
# Windows: C:\Users\YourName\ITAMeD_python\

# Then run test
python test_itamed.py
```

That's it! The package automatically finds it.

---

## Usage

### In Analysis Script

```python
# Method 1: Let package decide (automatic)
# Uses RMEA1D if ITAMeD not installed
python run_nmr_analysis.py

# Method 2: Specify explicitly
python run_nmr_analysis.py --method rmea1d   # Built-in
python run_nmr_analysis.py --method itamed    # ITAMeD (if installed)
```

### In Python Code

```python
from nmr_cpmg_analysis import perform_ilt

# RMEA1D (built-in, always available)
f, mc = perform_ilt(t, m, tau, lambda_opt, method='rmea1d')

# ITAMeD (if installed)
f, mc = perform_ilt(t, m, tau, lambda_opt, method='itamed')
```

---

## What's the Difference?

### RMEA1D (Built-in)
- ✅ Always available
- ✅ Fast (1-2 sec per file)
- ✅ Low CPU/memory usage
- ✅ Great for most data
- ⚠ Only L2 regularization

### ITAMeD (Optional)
- ✅ L1 regularization (sparse peaks)
- ✅ L2 regularization (smooth peaks)
- ✅ Better for some data types
- ⚠ Requires installation
- ⚠ Slower (5-10 sec per file)
- ⚠ Higher CPU usage

---

## Regularization Types

### L1 (Sparse)
- **Best for:** Sharp, discrete peaks
- **Think:** Few distinct T2 components
- **Example:** Water + bound water systems

### L2 (Smooth)
- **Best for:** Broad, continuous distributions
- **Think:** Continuous range of T2 values
- **Example:** Porous materials, complex mixtures

### RMEA1D (Tikhonov)
- **Best for:** Most experimental data
- **Think:** Balanced approach
- **Example:** General CPMG relaxation data

---

## Verification

### Run Test Script
```bash
python test_itamed.py
```

**Expected Output (ITAMeD installed):**
```
✓ ITAMeD AVAILABLE
✓ ITAMeD L2 AVAILABLE
```

**Expected Output (ITAMeD not installed):**
```
✗ ITAMeD NOT AVAILABLE
✓ RMEA1D ALWAYS AVAILABLE
```

### Check Analysis Output

When running analysis, look for:

**With ITAMeD:**
```
✓ ITAMeD module available
✓ ITAMeD L2 version available (for smooth, broad peaks)
    [DEBUG] Using ITAMeD method
```

**Without ITAMeD:**
```
⚠ ITAMeD module not available - only RMEA1D method will be available
    [DEBUG] Using RMEA1D method
```

---

## Common Myths

### Myth 1: "I must have ITAMeD"
**FALSE:** RMEA1D is robust and works great for 90%+ of applications.

### Myth 2: "ITAMeD always gives better results"
**FALSE:** Results depend on data type. Sometimes RMEA1D is better!

### Myth 3: "ITAMeD is too hard to install"
**FALSE:** Just download and extract to home directory. One step!

### Myth 4: "I can't compare methods without ITAMeD"
**FALSE:** RMEA1D alone can be compared across different datasets/parameters.

---

## When to Switch Methods

### Start with RMEA1D (built-in)
```bash
python run_nmr_analysis.py --method rmea1d
```

### If results look noisy
Try ITAMeD L2 (smooth):
```bash
# Install ITAMeD first
python run_nmr_analysis.py --method itamed
```

### If peaks look too broad
Try ITAMeD L1 (sparse):
```bash
python run_nmr_analysis.py --method itamed
# Or edit code to use L1 regularization
```

### If processing takes too long
Use RMEA1D (faster):
```bash
python run_nmr_analysis.py --method rmea1d
```

---

## Performance Comparison

| Metric | RMEA1D | ITAMeD |
|--------|---------|---------|
| **Speed** | Fast (1-2 sec) | Slower (5-10 sec) |
| **CPU** | Low | Moderate |
| **Memory** | Low | Moderate |
| **Setup** | None | Manual |
| **Reliability** | Very high | High |

---

## Quick Commands

```bash
# Test ITAMeD installation
python test_itamed.py

# Run with RMEA1D (default)
python run_nmr_analysis.py

# Run with ITAMeD
python run_nmr_analysis.py --method itamed

# Run specific file with RMEA1D
python run_nmr_analysis.py --method rmea1d --start 10 --end 20

# Run specific file with ITAMeD
python run_nmr_analysis.py --method itamed --start 10 --end 20
```

---

## FAQ (2-Second Answers)

**Q: Do I need ITAMeD?**
A: No, RMEA1D works great for most users.

**Q: How do I install ITAMeD?**
A: Download and extract to home directory. That's it.

**Q: Is ITAMeD better?**
A: Sometimes yes, sometimes no. Depends on your data.

**Q: Will my analysis fail without ITAMeD?**
A: No, it will use RMEA1D instead.

**Q: Can I switch between methods?**
A: Yes, use --method flag in command line.

**Q: Which should I use first?**
A: Start with RMEA1D. Only try ITAMeD if needed.

---

## Installation Checklist

- [ ] Download ITAMeD_python from GitHub
- [ ] Extract to: `~/ITAMeD_python/` (Linux/Mac) or `C:\Users\YourName\ITAMeD_python\` (Windows)
- [ ] Run: `python test_itamed.py`
- [ ] Verify: "✓ ITAMeD AVAILABLE"
- [ ] Run analysis: `python run_nmr_analysis.py`

---

## Documentation Links

- **ITAMED_INSTALLATION.md** - Complete installation guide
- **README.md** - Main package documentation
- **USER_GUIDE.md** - Detailed user guide
- **test_itamed.py** - Test script with diagnostics

---

## Bottom Line

**For 90% of users:** Use RMEA1D (built-in) - it works great!

**For advanced users:** Install ITAMeD if you need:
- L1/L2 regularization
- Sparse peak detection
- Better low-SNR performance
- Method comparison

**RMEA1D is NOT a fallback** - it's a robust, well-tested method that's perfect for most NMR analysis tasks.

---

## Quick Reference Card

```
RMEA1D:
  • Built-in, always available
  • Fast, reliable
  • Great for most data
  • Command: --method rmea1d

ITAMeD:
  • Optional, requires installation
  • Slower but more features
  • L1 (sparse) or L2 (smooth)
  • Command: --method itamed

Test:
  • Command: python test_itamed.py
  • Verify installation status
  • Check Python path

Docs:
  • ITAMED_INSTALLATION.md (detailed)
  • README.md (general)
  • test_itamed.py (diagnostics)
```

---

**Remember:** You can ALWAYS use RMEA1D. ITAMeD is optional!

