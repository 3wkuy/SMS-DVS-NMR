# User Guide - CPMG NMR Data Processing

## Table of Contents

1. [Introduction](#introduction)
2. [Installation](#installation)
3. [Getting Started](#getting-started)
4. [Understanding the Interface](#understanding-the-interface)
5. [Data Requirements](#data-requirements)
6. [Output Files](#output-files)
7. [Advanced Usage](#advanced-usage)
8. [Troubleshooting](#troubleshooting)
9. [FAQ](#faq)

---

## Introduction

This package provides comprehensive tools for processing CPMG (Carr-Purcell-Meiboom-Gill) NMR relaxation data using Inverse Laplace Transform (ILT) analysis. It includes:

- **T2 Distribution Analysis**: Compute T2 relaxation time distributions from CPMG data
- **Multiple ILT Methods**: Support for RMEA1D (built-in) and ITAMeD (optional)
- **Automatic Parameter Optimization**: Find optimal regularization parameters automatically
- **Batch Processing**: Process multiple files efficiently
- **Rich Visualizations**: Generate publication-quality plots
- **Peak Analysis**: Identify and integrate peaks in T2 distributions

---

## Installation

### Option 1: Automated Installation (Recommended)

#### Windows
1. Download and extract the package
2. Double-click `install.bat`
3. Wait for installation to complete
4. Run `python run_nmr_analysis.py`

#### Linux/Mac
1. Download and extract the package
2. Open terminal in package directory
3. Run: `chmod +x install.sh && ./install.sh`
4. Run: `python3 run_nmr_analysis.py`

### Option 2: Manual Installation

1. Ensure Python 3.7+ is installed
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the analysis script

### Required Python Packages

- `numpy` (>=1.21.0): Numerical computing
- `matplotlib` (>=3.5.0): Plotting and visualization
- `scipy` (>=1.7.0): Scientific computing
- `pandas` (>=1.3.0): Data manipulation
- `pywin32` (>=305): Windows Excel integration (Windows only, optional)

---

## Getting Started

### Running Your First Analysis

1. **Start the program:**
   ```bash
   python run_nmr_analysis.py
   ```

2. **Select a dataset:**
   - Choose a pre-configured dataset (1-10) OR
   - Select 0 for custom dataset

3. **Configure parameters:**
   - Confirm file range or specify custom range
   - Choose processing method (rmea1d or itamed)
   - Set truncation range if needed

4. **Wait for processing:**
   - Progress will be displayed
   - Time depends on file count and computer speed

5. **View results:**
   - Results are saved in the data directory
   - Check the output subdirectory

### Example Session

```
============================================
CPMG NMR Data Processing with ILT Analysis
============================================

Available Datasets:
1. LiCl Dataset
2. Mg(NO3)2 Dataset
3. Lewatit Water Dataset
...
0. Custom (specify paths)

Select a dataset (0-10): 1

Dataset: LiCl Dataset
Base directory: E:/SMS-NMR/Data/LiCl/LiCl/
Filename prefix: CPMG_relaxorption_T2_LiCl_

File range: 40 to 188
Reference file: 152

Use these settings? (y/n): y

Processing files...
[████████████████████████████████████████] 100% complete

Analysis complete!
Results saved to: E:/SMS-NMR/Data/LiCl/LiCl/ILT_Results/
```

---

## Understanding the Interface

### Main Menu Options

The main interface provides:

1. **Dataset Selection**: Choose from pre-configured or custom datasets
2. **Parameter Configuration**: Set file ranges, processing methods
3. **Batch Processing**: Process multiple files automatically
4. **Result Visualization**: View generated plots and data

### Processing Parameters

#### File Range
- **Start File**: First file number to process
- **End File**: Last file number to process
- **Reference File**: File used for lambda optimization (affects all files)

#### Processing Method
- **rmea1d**: Built-in method, always available
  - Fast and reliable
  - Good for most applications
  - Uses regularized multi-exponential analysis

- **itamed**: Optional advanced method
  - Provides potentially better results
  - Better for sparse/sharp peaks
  - Requires ITAMeD_python package

#### Truncation
- **Start Time**: Exclude data before this time (ms)
- **End Time**: Exclude data after this time (ms)
- **Purpose**: Remove noise or focus on relevant time range

---

## Data Requirements

### File Format

The package expects CPMG NMR data from TNMR software:

1. **File Naming Convention**:
   - Follow pattern: `PREFIX_001.ext`
   - Examples:
     - `CPMG_relaxorption_T2_LiCl_001.csv`
     - `CPMG_Urea_20250904_006.csv`

2. **File Contents**:
   - Time (ms) column
   - Signal (amplitude) column
   - May include additional metadata

3. **Directory Structure**:
   ```
   base_directory/
   ├── PREFIX_001.csv
   ├── PREFIX_002.csv
   ├── PREFIX_003.csv
   └── ...
   ```

### Supported File Types

- CSV (Comma Separated Values)
- May support other formats with modification

### Data Quality Requirements

- **Signal-to-Noise**: Adequate SNR for reliable analysis
- **Time Range**: Sufficient echo trains to capture relaxation
- **Consistency**: Similar acquisition parameters across files

---

## Output Files

### Directory Structure

```
base_directory/
├── original_files/
├── ILT_Results/
│   ├── plots/
│   │   ├── T2_distributions/
│   │   ├── fitting_results/
│   │   ├── L_curves/
│   │   └── peak_integration/
│   ├── processed_data/
│   │   ├── T2_distributions/
│   │   ├── fitting_results/
│   │   └── peak_analysis/
│   └── summaries/
│       └── T2_summary.csv
└── report.txt
```

### Output File Types

#### 1. Plots
- **T2 Distributions**: 2D heatmaps and 1D distribution curves
- **Fitting Results**: Original and fitted data overlay
- **L-Curves**: Regularization parameter optimization
- **Peak Integration**: Peak identification and area calculation

#### 2. Processed Data
- **T2 Distributions**: CSV files with T2 values and amplitudes
- **Fitting Parameters**: Exponential fit coefficients
- **Peak Areas**: Integrated peak areas for each component

#### 3. Summary Files
- **T2 Summary**: Comprehensive summary of all results
- **Report**: Text-based analysis report

### File Naming Convention

- Original: `PREFIX_XXX.csv`
- Processed: `PREFIX_XXX_T2.csv`
- Plot: `PREFIX_XXX_T2_distribution.png`
- Summary: `T2_summary.csv`

---

## Advanced Usage

### Custom Dataset Configuration

To add a new dataset, modify the `datasets` dictionary:

```python
datasets = {
    'my_dataset': {
        'name': 'My Custom Dataset',
        'base_dir': 'path/to/my/data/',
        'filename_prefix': 'custom_prefix_',
        'reference_file': 10,
        'default_start': 1,
        'default_end': 50
    }
}
```

### Command Line Usage

For batch processing without prompts:

```bash
python run_nmr_analysis.py --mode all --start 1 --end 100 --base-dir "E:/Data/" --filename-prefix "CPMG_" --reference-file 50
```

Arguments:
- `--mode`: 'all' or 'jump4' (every 4th file)
- `--start`: Starting file number
- `--end`: Ending file number
- `--base-dir`: Data directory path
- `--filename-prefix`: File naming prefix
- `--reference-file`: Reference file for lambda optimization
- `--truncate`: Time range for truncation (e.g., '0-450')

### Using as a Python Module

```python
from nmr_cpmg_analysis import perform_ilt, find_optimal_lambda
import numpy as np

# Load your data
time = np.loadtxt('my_data.csv', usecols=0)  # Time in ms
signal = np.loadtxt('my_data.csv', usecols=1)  # Signal
tau = np.logspace(-1, 3, 100)  # T2 grid

# Find optimal lambda
lambda_opt = find_optimal_lambda(time, signal, tau)

# Perform ILT
t2_distribution, fitted_signal = perform_ilt(
    time, signal, tau, lambda_opt, method='rmea1d'
)

# Analyze results
print(f"T2 distribution: {len(t2_distribution)} points")
print(f"Peak T2 value: {tau[np.argmax(t2_distribution)]:.2f} ms")
```

### Batch Processing Script

```python
from nmr_cpmg_analysis import build_processing_plan, main
import sys

# Configure batch processing
plan = build_processing_plan(
    file_numbers=range(1, 101),  # Files 1-100
    base_dir='E:/SMS-NMR/Data/MyDataset/',
    filename_prefix='CPMG_',
    label_prefix='Sample_'
)

# Run processing
sys.argv = ['run_nmr_analysis.py',
            '--mode', 'all',
            '--start', '1',
            '--end', '100',
            '--base-dir', 'E:/SMS-NMR/Data/MyDataset/',
            '--filename-prefix', 'CPMG_',
            '--reference-file', '50']

main()
```

---

## Troubleshooting

### Common Issues

#### 1. Python Not Found
**Problem**: "python is not recognized as an internal or external command"

**Solution**:
- Install Python 3.7+ from https://www.python.org/downloads/
- During installation, check "Add Python to PATH"
- Restart command prompt/terminal after installation

#### 2. Import Errors
**Problem**: "ModuleNotFoundError: No module named 'numpy'"

**Solution**:
```bash
pip install -r requirements.txt
```

#### 3. File Not Found
**Problem**: "FileNotFoundError: [Errno 2] No such file or directory"

**Solution**:
- Check file paths are correct
- Use absolute paths
- On Windows, use forward slashes (/) instead of backslashes (\)
- Verify files exist in the specified directory

#### 4. Memory Issues
**Problem**: "MemoryError" or program crashes with large datasets

**Solution**:
- Process files in smaller batches
- Reduce T2 grid size (fewer tau points)
- Use `--mode jump4` to process fewer files
- Close other programs to free memory

#### 5. ITAMeD Not Available
**Problem**: "ITAMeD module not available - only RMEA1D method will be available"

**Solution**:
- This is a warning, not an error
- RMEA1D method works fine without ITAMeD
- To use ITAMeD, install from: https://github.com/your-repo/ITAMeD_python

#### 6. Poor Quality Results
**Problem**: T2 distributions look noisy or unrealistic

**Solution**:
- Check data quality (SNR, noise levels)
- Try different lambda optimization methods
- Adjust truncation range
- Try different ILT methods (rmea1d vs itamed)
- Verify data format is correct

### Debugging Tips

1. **Enable verbose output**:
   - The script prints progress messages
   - Check for error messages or warnings

2. **Test with a single file**:
   ```bash
   python run_nmr_analysis.py --start 50 --end 50
   ```

3. **Check output directory**:
   - Ensure you have write permissions
   - Verify sufficient disk space

4. **Verify Python version**:
   ```bash
   python --version
   ```
   Must be 3.7 or higher

---

## FAQ

### Q: Can I process data from other NMR instruments?
A: The package is designed for TNMR software data. Other formats may require file format conversion or modification of the data loading code.

### Q: How long does processing take?
A: Depends on:
- Number of files
- Data length per file
- T2 grid size
- Computer speed

Typical: 1-10 seconds per file

### Q: What's the difference between RMEA1D and ITAMeD?
A:
- **RMEA1D**: Built-in, fast, good for most data
- **ITAMeD**: Advanced, optional, may give better results for sparse data

### Q: How do I choose the lambda parameter?
A: The package automatically finds optimal lambda using:
- L-curve method
- Balanced approach
- You can also specify manually

### Q: Can I process data without the TNMR software?
A: Yes, if your data is in the correct format (time and signal columns in CSV files).

### Q: What if my data has different units?
A: The package expects:
- Time in milliseconds (ms)
- Signal in arbitrary units (amplitude)
- T2 in milliseconds (ms)

Convert your data if needed.

### Q: Can I use this for T1 (spin-lattice) relaxation?
A: The code is designed for T2 (spin-spin) relaxation. T1 processing would require modifications to handle inversion recovery data.

### Q: How do I cite this package?
A: Please include a reference to this package and the ILT methods used in your publications.

### Q: Is there a GUI version?
A: Currently, the package uses a command-line interface. A GUI may be added in future versions.

### Q: Can I use this on a Mac/Linux?
A: Yes, the package is cross-platform. Some Windows-specific features (like Excel integration) won't work on other systems.

### Q: Where can I get help?
A:
- Check this user guide
- See README.md for general information
- Check the code comments for technical details
- Contact the package maintainer for specific issues

---

## Technical Details

### ILT Methods

#### RMEA1D
Regularized Multi-Exponential Analysis (1D) using Tikhonov regularization.

**Equation**: minimize ||A f - m||² + λ||L f||²

Where:
- A: Exponential kernel matrix
- f: T2 distribution (unknown)
- m: Measured signal
- λ: Regularization parameter
- L: Regularization operator

#### ITAMeD
Iterative Adaptive Approach for Multi-Exponential Decay analysis using sparsity-promoting regularization.

**Advantages**:
- Better for sparse/sharp peaks
- L1 regularization promotes sparsity
- L2 regularization for smooth peaks

### Lambda Optimization

#### L-Curve Method
- Plot residual norm vs. solution norm for various λ
- Find corner of L-shaped curve
- Balance between fit and smoothness

#### Balanced Method
- Consider both data fit and solution smoothness
- Choose λ that balances residuals and regularization term
- Good compromise approach

### T2 Grid Construction

The T2 grid is logarithmically spaced:
```python
tau = np.logspace(tau_min, tau_max, n_points)
```

Typical values:
- tau_min: -1 (0.1 ms)
- tau_max: 3 (1000 ms)
- n_points: 100-200

---

## Version History

### Version 1.3.0
- Initial packaged release
- Cross-platform support
- Automated installation scripts
- Enhanced documentation
- Multiple pre-configured datasets

---

## Support and Development

For bug reports, feature requests, or contributions:
- [GitHub Repository](https://github.com/your-repo/nmr-cpmg-analysis)
- [Documentation](https://your-repo.github.io/nmr-cpmg-analysis/)
- [Issues](https://github.com/your-repo/nmr-cpmg-analysis/issues)

---

## License

[Add your license information here]

---

## Acknowledgments

This package uses:
- NumPy, SciPy, Matplotlib, Pandas for data processing and visualization
- ITAMeD for advanced ILT analysis (optional)

Special thanks to the NMR research community for feedback and testing.

---

**End of User Guide**

