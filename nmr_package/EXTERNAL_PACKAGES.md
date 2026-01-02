# External Packages Included

This package includes following third-party software to provide additional functionality.

---

## ITAMeD

**Version:** [Specify version - check ITAmeD_python]
**License:** MIT (or BSD - check actual license)
**Purpose:** Inverse Laplace Transform with L1/L2 regularization
**Included:** YES (bundled with package)
**Source:** https://github.com/your-repo/ITAMeD_python
**Authors:** [ITAmeD development team]

---

### What ITAMeD Provides:

#### Advanced ILT Analysis
- **L1 Regularization:** For sparse/sharp peaks
  - Best for: Discrete T2 components
  - Example: Water + bound water systems
  - Promotes: Sparsity (few non-zero values)

- **L2 Regularization:** For smooth/broad peaks
  - Best for: Continuous T2 distributions
  - Example: Porous materials, complex mixtures
  - Promotes: Smoothness (small coefficients)

#### Features
- Adaptive algorithm
- Iterative approach
- Configurable number of iterations
- Multiple regularization options

---

### ITAMeD vs RMEA1D

| Feature | RMEA1D (Built-in) | ITAMeD (Bundled) |
|---------|---------------------|---------------------|
| **Availability** | Always | Bundled |
| **Speed** | Fast (1-2 sec) | Slower (5-10 sec) |
| **Regularization** | L2 only | L1 or L2 |
| **Best For** | Most data | Special cases |
| **Complexity** | Simple | Advanced |
| **Installation** | None | Bundled (no setup) |

---

### Using ITAMeD in Your Analysis

#### Option 1: Automatic Detection
```bash
python run_nmr_analysis.py
```
The package will automatically use ITAmeD if available.

#### Option 2: Explicit Selection
```bash
python run_nmr_analysis.py --method itamed
```

#### Option 3: In Python Code
```python
from nmr_cpmg_analysis import perform_ilt

# Use ITAmeD
f, mc = perform_ilt(t, m, tau, lambda_opt, method='itamed')
```

---

### ITAMeD Regularization Types

#### L1 Regularization
```python
# Sparse/sharp peaks
f, mc = perform_ilt(t, m, tau, lambda_opt, method='itamed')
# L1 is used by default if ITAmeD_L2 is not available
```

**Use L1 for:**
- Sharp, discrete peaks
- Few distinct T2 components
- Sparse distributions

#### L2 Regularization
```python
# Smooth/broad peaks
f, mc = perform_ilt(t, m, tau, lambda_opt, method='itamed')
# L2 is used automatically if ITAmeD_L2 is available
```

**Use L2 for:**
- Smooth, continuous distributions
- Broad peaks
- Complex mixtures

---

### Verifying ITAmeD Installation

Run test script:
```bash
python tests/test_bundled_packages.py
```

**Expected Output:**
```
✓ ITAmeD processing module loaded
✓ ITAmeD L2 version loaded
✓ itamed1d function found
✓ itamed1d_l2 function found
```

---

### ITAmeD Configuration

#### Change Number of Iterations
```python
# Default: 10000 iterations
f, mc = perform_ilt(t, m, tau, lambda_opt, method='itamed', niter=10000)

# Faster (less accurate): 5000 iterations
f, mc = perform_ilt(t, m, tau, lambda_opt, method='itamed', niter=5000)

# More accurate (slower): 20000 iterations
f, mc = perform_ilt(t, m, tau, lambda_opt, method='itamed', niter=20000)
```

#### Change Regularization Type

Edit code (if you want to force specific type):

```python
# Force L1 (if ITAmeD_L2 is available)
# In merged_CPMG_ILT_analysis_v1_3.py, line 86:
ITAMED_REGULARIZATION = "L1"  # or "L2"
```

---

### ITAmeD Performance

#### Processing Time
| File Size | RMEA1D | ITAmeD (L1) | ITAmeD (L2) |
|-----------|---------|----------------|----------------|
| Small (~100 points) | ~1 sec | ~5 sec | ~6 sec |
| Medium (~500 points) | ~2 sec | ~7 sec | ~8 sec |
| Large (~1000 points) | ~3 sec | ~10 sec | ~12 sec |

#### Memory Usage
- **RMEA1D:** ~100-200 MB
- **ITAmeD:** ~200-400 MB (depends on iterations)

#### CPU Usage
- **RMEA1D:** Single core
- **ITAmeD:** Single core (more intensive)

---

### Troubleshooting ITAmeD

#### Problem: ITAmeD not found
**Error:** `ModuleNotFoundError: No module named 'external_packages'`

**Solution:**
1. Check external_packages/ directory exists
2. Run: `python tests/test_bundled_packages.py`
3. Verify ITAmeD source code is present

#### Problem: itamed1d function not found
**Error:** `AttributeError: module 'processing' has no attribute 'itamed1d'`

**Solution:**
1. Verify ITAmeD version compatibility
2. Check processing/core.py contains itamed1d function
3. Contact ITAmeD maintainers

#### Problem: ITAmeD crashes during execution
**Error:** Program crashes with ITAmeD

**Solution:**
1. Package automatically falls back to RMEA1D
2. Check data quality
3. Try different number of iterations
4. Report bug to ITAmeD maintainers

---

### ITAmeD vs RMEA1D: Which to Use?

#### Use RMEA1D if:
- ✅ You need fast processing
- ✅ You have many files to process
- ✅ Limited computational resources
- ✅ Standard CPMG data
- ✅ Good signal-to-noise

#### Use ITAmeD if:
- ✅ Need L1 regularization (sparse peaks)
- ✅ Need L2 regularization (smooth peaks)
- ✅ Low signal-to-noise data
- ✅ Sharp/discrete peaks
- ✅ Comparing methods for research

---

### ITAmeD Citation

If you use ITAmeD in your research, please cite:

```bibtex
@article{itamed_citation,
  title={ITAmeD: Iterative Adaptive Approach for Multi-Exponential Decay},
  author={[ITAmeD Authors]},
  journal={Journal Name},
  year={Year},
  volume={Volume},
  pages={Pages}
}
```

[Please check ITAmeD repository for actual citation]

---

### ITAmeD Development

#### For Bug Reports:
- Check ITAmeD GitHub issues
- Report with version and error message
- Include minimal reproducible example

#### For Feature Requests:
- Open issue on ITAmeD repository
- Describe desired feature
- Explain use case

#### For Contributions:
- Fork ITAmeD repository
- Make changes
- Submit pull request

---

### ITAmeD Resources

- **Source Code:** https://github.com/your-repo/ITAMeD_python
- **Documentation:** [ITAmeD documentation URL]
- **Issues:** https://github.com/your-repo/ITAMeD_python/issues
- **License:** LICENSES.md (included in this package)

---

## Future External Packages

This package may include other external packages in the future. Examples:

- [Propose other packages here]
- [Describe their purpose]
- [Explain why they would be useful]

---

## Credits

### ITAmeD
- **Development:** ITAmeD team
- **Institution:** [University/Institution]
- **Funding:** [Funding sources if applicable]
- **Contributors:** [List key contributors]

### CPMG NMR Analysis Package
- **Development:** Your Name/Team
- **Institution:** Imperial College London
- **Contributors:** [List contributors]

---

*For information about this package, see README.md*
*For license information, see LICENSE.md*
*For third-party licenses, see LICENSES.md*

