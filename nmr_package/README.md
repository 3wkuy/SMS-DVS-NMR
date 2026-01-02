# CPMG NMR Data Processing Package

A comprehensive Python package for processing CPMG NMR data from TNMR software with advanced Inverse Laplace Transform (ILT) analysis.

## Features

- T2 fitting and analysis
- Inverse Laplace Transform (ILT) with automatic lambda optimization
- Support for RMEA1D and ITAMeD methods
- Multiple dataset support with pre-configured processing parameters
- Batch processing capabilities
- Rich visualization and reporting
- Peak integration and analysis
- Cross-platform support (Windows, Linux, Mac)

## Requirements

- Python 3.7 or higher
- pip package manager (comes with Python)

## Quick Start

### Windows Users

1. **Double-click** `install.bat` to automatically install all dependencies
2. Run the analysis: `python run_nmr_analysis.py`
3. Follow the on-screen prompts to select your dataset

### Linux/Mac Users

1. **Run** `chmod +x install.sh && ./install.sh` to install dependencies
2. Run the analysis: `python run_nmr_analysis.py`
3. Follow the on-screen prompts to select your dataset

**Note:** For advanced ITAMeD features (optional), see [ITAMED_INSTALLATION.md](ITAMED_INSTALLATION.md)

## Manual Installation

If automated scripts don't work, manually install dependencies:

```bash
pip install -r requirements.txt
```

Or install individually:

```bash
pip install numpy matplotlib scipy pandas
```

*Note: Windows users need pywin32 for Excel integration (optional):*

```bash
pip install pywin32
```

## Usage

### Basic Usage

```python
python run_nmr_analysis.py
```

The script will guide you through:
1. Selecting a dataset (or provide custom paths)
2. Choosing file range
3. Setting processing parameters
4. Viewing results

### Command Line Arguments

```bash
python run_nmr_analysis.py --mode all --start 1 --end 100 --base-dir "path/to/data" --filename-prefix "CPMG_" --reference-file 50
```

Available arguments:
- `--mode`: Process 'all' files or 'jump4' (every 4th file)
- `--start`: First file number (default: 1)
- `--end`: Last file number (default: varies by dataset)
- `--base-dir`: Base directory path for data files
- `--filename-prefix`: Filename prefix pattern
- `--reference-file`: File number for lambda optimization
- `--truncate`: Truncate data to time range (e.g., '0-450')

### Using in Python Code

```python
from nmr_cpmg_analysis import perform_ilt, rmea1d, find_optimal_lambda

# Load your data
t = np.array([0.1, 0.2, 0.3, ...])  # Time points
m = np.array([1.0, 0.9, 0.8, ...])  # Signal measurements
tau = np.logspace(-1, 3, 100)      # Time constants

# Find optimal lambda
lambda_opt = find_optimal_lambda(t, m, tau)

# Perform ILT using RMEA1D (built-in, always available)
f, mc = perform_ilt(t, m, tau, lambda_opt, method='rmea1d')

# Or use ITAMeD (optional, requires installation)
# f, mc = perform_ilt(t, m, tau, lambda_opt, method='itamed')

# Analyze results
print(f"T2 distribution computed with {len(f)} points")
```

**Note:** See [ITAMED_INSTALLATION.md](ITAMED_INSTALLATION.md) for ITAMeD setup instructions.

## Pre-configured Datasets

The package includes several pre-configured datasets:

1. LiCl Dataset
2. Mg(NO3)2 Dataset
3. Lewatit Water Dataset
4. Urea Dataset
5. LiCl Dataset (0.8T)
6-8. Avicel Water Datasets (1-3)
9. LiCl Dataset (0.5T, Gain=600dB)
10. LiCl Dataset (1211)

You can easily add more datasets by modifying the `datasets` dictionary in the main script.

## Output Files

The analysis generates:

- **ILT Results**: T2 distributions with optimal regularization
- **T2 Fitting**: Multi-exponential fitting results
- **Peak Analysis**: Peak identification and integration
- **Visualizations**: Multiple plots including:
  - Raw and processed data
  - T2 distributions
  - L-curves for lambda optimization
  - Peak integration verification
- **Summary Reports**: CSV files with processed data and results

## Project Structure

```
nmr-package/
├── requirements.txt              # Python dependencies
├── setup.py                      # Package setup script
├── install.bat                   # Windows installer
├── install.sh                    # Linux/Mac installer
├── run_nmr_analysis.py           # Main execution script
├── README.md                     # This file
└── nmr_cpmg_analysis/
    ├── __init__.py              # Package initialization
    └── merged_CPMG_ILT_analysis_v1.3.py  # Core analysis module
```

## Troubleshooting

### Import Errors

If you see import errors:
1. Make sure you've installed all dependencies: `pip install -r requirements.txt`
2. Check Python version: `python --version` (must be 3.7+)
3. Try reinstalling: `pip install --upgrade -r requirements.txt`

### Windows-Specific Issues

If you encounter issues with pywin32:
- Run: `python Scripts/pywin32_postinstall.py -install`
- Or install: `pip install --force-reinstall pywin32`

### Path Issues

If the script can't find your data:
1. Use absolute paths (e.g., `E:/SMS-NMR/Data/...`)
2. Ensure forward slashes (/) or escaped backslashes (\\)
3. Check file permissions

### ITAMeD Module Not Available

The package includes a fallback RMEA1D method, so ITAMeD is optional:
- RMEA1D is always available (built-in) and works great for most applications
- ITAMeD provides additional features (L1/L2 regularization) but requires manual installation

**For ITAMeD installation instructions, see [ITAMED_INSTALLATION.md](ITAMED_INSTALLATION.md)**

## Advanced Usage

### Custom Dataset Configuration

Add your dataset to the `datasets` dictionary:

```python
datasets = {
    'custom': {
        'name': 'My Dataset',
        'base_dir': 'path/to/your/data/',
        'filename_prefix': 'your_prefix_',
        'reference_file': 10,
        'default_start': 1,
        'default_end': 50
    }
}
```

### ILT Method Selection

Choose between ILT methods:

```python
# RMEA1D (built-in, always available)
f, mc = perform_ilt(t, m, tau, lambda_opt, method='rmea1d')

# ITAMeD (if installed, provides better results for sparse data)
f, mc = perform_ilt(t, m, tau, lambda_opt, method='itamed', niter=10000)
```

### Lambda Optimization

Several methods for finding optimal lambda:

```python
# Balanced method (recommended)
lambda_opt = find_optimal_lambda(t, m, tau, lambda_opt_method='balanced')

# L-curve corner
lambda_opt = find_optimal_lambda(t, m, tau, lambda_opt_method='lcurve')

# Manual selection
lambda_opt = 1e-3
```

## Citation

If you use this package in your research, please cite:

[Add your citation information here]

## License

[Add your license information here]

## Contact

For questions, issues, or contributions:
[Add contact information here]

## Changelog

### Version 1.3.0
- Initial package release
- Support for multiple datasets
- Enhanced visualization
- Improved error handling

