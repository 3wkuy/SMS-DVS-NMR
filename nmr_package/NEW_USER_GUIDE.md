# New User Guide - CPMG NMR Analysis Package

Welcome! This guide will walk you through using the CPMG NMR Data Processing Package from scratch.

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [First Steps](#first-steps)
4. [Running Your First Analysis](#running-your-first-analysis)
5. [Understanding the Results](#understanding-the-results)
6. [Common Use Cases](#common-use-cases)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

Before you start, make sure you have:

- **Python 3.7 or higher** installed
  - Check by running: `python --version` or `python3 --version`
  - If not installed: Download from [python.org](https://www.python.org/downloads/)
  - **Important for Windows**: Check "Add Python to PATH" during installation

- **Your NMR data files** in CSV format
  - Column 0: Time (in milliseconds)
  - Column 1: Signal (amplitude)
  - Example filename: `CPMG_LiCl_001.csv`, `CPMG_LiCl_002.csv`, etc.

---

## Installation

### Step 1: Get the Package

If you haven't already, download or clone the package:
```bash
git clone https://github.com/3wkuy/SMS-DVS-NMR.git
cd SMS-DVS-NMR/nmr_package
```

### Step 2: Install Dependencies

#### **Windows Users (Easiest Method):**

1. Open File Explorer and navigate to the `nmr_package` folder
2. **Double-click** the file `install.bat`
3. A black command window will appear
4. Wait 2-5 minutes for installation to complete
5. You'll see "Installation completed successfully!" when done

#### **Linux/Mac Users:**

1. Open a terminal in the `nmr_package` directory
2. Run:
   ```bash
   chmod +x install.sh
   ./install.sh
   ```
3. Wait for installation to complete

#### **Manual Installation (If automated scripts don't work):**

Open a terminal/command prompt in the `nmr_package` directory and run:
```bash
pip install -r requirements.txt
```

Or install packages individually:
```bash
pip install numpy matplotlib scipy pandas
```

**Windows users (optional):**
```bash
pip install pywin32
```

### Step 3: Verify Installation

Test that everything works:
```bash
python test_package.py
```

You should see:
```
✓ Package imported successfully!
✓ All core functions are working correctly!
```

---

## First Steps

### Understanding Your Data

Your data should be organized like this:

```
MyData/
├── CPMG_LiCl_001.csv
├── CPMG_LiCl_002.csv
├── CPMG_LiCl_003.csv
└── ...
```

Each CSV file should contain:
- **Column 0**: Time values (in milliseconds)
- **Column 1**: Signal amplitude values

Example CSV content:
```csv
Time_ms,Signal
0.1,1.000
0.2,0.950
0.3,0.901
...
```

---

## Running Your First Analysis

### Method 1: Interactive Mode (Recommended for Beginners)

This is the easiest way to get started:

1. **Open a terminal/command prompt**

2. **Navigate to the package directory:**
   ```bash
   cd path/to/SMS-DVS-NMR/nmr_package
   ```

3. **Run the main script:**
   ```bash
   python run_nmr_analysis.py
   ```

4. **Follow the prompts:**

   ```
   ============================================================
   CPMG NMR Data Processing with ILT Analysis
   ============================================================
   
   Available datasets:
   1. LiCl Dataset
   2. Mg(NO3)2 Dataset
   3. Lewatit Water Dataset
   ...
   0. Custom dataset
   
   Select a dataset (0-10): 
   ```

   - **If you have a pre-configured dataset**: Enter the number (1-10)
   - **If you have your own data**: Enter `0` and provide:
     - Base directory path (e.g., `E:/MyNMRData/`)
     - Filename prefix (e.g., `CPMG_`)
     - Reference file number

5. **Confirm settings:**
   ```
   Processing settings:
   - Mode: all
   - Start file: 1
   - End file: 100
   - Reference file: 50
   
   Use these settings? (y/n): y
   ```

6. **Wait for processing** (may take several minutes)

7. **Results will be saved** in your data directory under `ILT_Results/`

### Method 2: Quick Test with Synthetic Data

To test the package without real data:

```bash
python examples/simple_example.py
```

This will:
- Generate synthetic CPMG data
- Perform ILT analysis
- Show you example results

### Method 3: Command Line Mode (Advanced)

For batch processing without prompts:

```bash
python run_nmr_analysis.py --mode all --start 1 --end 100 --base-dir "E:/Data/" --filename-prefix "CPMG_" --reference-file 50
```

**Arguments:**
- `--mode`: `all` (all files) or `jump4` (every 4th file)
- `--start`: First file number
- `--end`: Last file number
- `--base-dir`: Path to your data directory
- `--filename-prefix`: Your file prefix (e.g., `CPMG_`)
- `--reference-file`: File number for lambda optimization
- `--truncate`: Time range (e.g., `0-450`)

---

## Understanding the Results

After processing, you'll find results in your data directory:

```
YourDataDirectory/
└── ILT_Results/
    ├── ILT_distributions.csv      # T2 distributions
    ├── T2_fitting_results.csv     # Fitting parameters
    ├── peak_analysis.csv           # Peak identification
    └── plots/                      # Visualization plots
        ├── T2_distributions.png
        ├── L_curve.png
        └── ...
```

### Key Output Files:

1. **ILT_distributions.csv**: T2 relaxation time distributions
   - Columns: T2 values (ms), Amplitude

2. **T2_fitting_results.csv**: Multi-exponential fitting results
   - Contains fitted parameters for each file

3. **peak_analysis.csv**: Identified peaks and their integrals
   - Peak positions, widths, and areas

4. **Plots**: Visual representations of your data and results

---

## Common Use Cases

### Use Case 1: Process a Single File

```python
from nmr_cpmg_analysis import perform_ilt, find_optimal_lambda
import numpy as np

# Load your data
data = np.loadtxt('my_data.csv', delimiter=',', skiprows=1)
t = data[:, 0]  # Time in ms
m = data[:, 1]  # Signal

# Create T2 grid
tau = np.logspace(0, 3, 100)  # 1 to 1000 ms

# Find optimal lambda
lambda_opt = find_optimal_lambda(t, m, tau)

# Perform ILT
f, mc = perform_ilt(t, m, tau, lambda_opt, method='rmea1d')

# Analyze results
peak_t2 = tau[np.argmax(f)]
print(f"Peak T2: {peak_t2:.2f} ms")
```

### Use Case 2: Batch Process Multiple Files

Use the interactive mode or command line mode (see above).

### Use Case 3: Custom Analysis

```python
from nmr_cpmg_analysis import perform_ilt, find_optimal_lambda, rmea1d
import numpy as np

# Your data
t = np.array([...])  # Time points
m = np.array([...])  # Signal
tau = np.logspace(-1, 3, 100)  # T2 grid

# Find optimal lambda with custom method
lambda_opt = find_optimal_lambda(
    t, m, tau, 
    method='rmea1d',
    lambda_opt_method='balanced'  # or 'lcurve'
)

# Perform ILT
f, mc = perform_ilt(t, m, tau, lambda_opt, method='rmea1d')

# Save results
np.savetxt('results.csv', 
           np.column_stack([tau, f]), 
           delimiter=',', 
           header='T2_ms,Amplitude', 
           comments='')
```

---

## Troubleshooting

### Problem: "Python not found" or "python is not recognized"

**Solution:**
- Python is not installed or not in PATH
- Install Python 3.7+ from [python.org](https://www.python.org/downloads/)
- **Critical**: Check "Add Python to PATH" during installation
- Restart your terminal after installation

### Problem: "ModuleNotFoundError: No module named 'numpy'"

**Solution:**
```bash
pip install -r requirements.txt
```

Make sure you're in the `nmr_package` directory.

### Problem: "FileNotFoundError: No such file or directory"

**Solution:**
- Use **absolute paths** (e.g., `E:/Data/` not just `Data/`)
- On Windows, use forward slashes (`/`) instead of backslashes (`\`)
- Verify files exist in the specified directory
- Check file permissions

### Problem: "ITAMeD module not available"

**Solution:**
- This is a **WARNING**, not an error
- The **RMEA1D method works perfectly** without ITAMeD
- ITAMeD is optional and provides advanced features
- You can ignore this warning for basic usage

### Problem: Program runs slowly

**Solution:**
- Process fewer files at a time
- Use `--mode jump4` to process every 4th file
- Close other programs to free memory
- Ensure you have at least 4GB RAM (8GB recommended)

### Problem: Results look wrong or noisy

**Solution:**
- Check data quality (SNR, noise levels)
- Try different truncation ranges (`--truncate 0-450`)
- Verify data format (time in ms, signal in amplitude)
- Try different ILT methods (rmea1d vs itamed)

---

## Getting Help

### Documentation Files

- **README.md** - Main documentation
- **QUICKSTART.md** - 5-minute quick start
- **USER_GUIDE.md** - Detailed user guide
- **INSTRUCTIONS.txt** - Complete setup instructions

### Example Code

- **examples/simple_example.py** - Basic usage examples
- **test_package.py** - Package verification script

### Still Need Help?

1. Check the error message carefully
2. Read the relevant documentation file
3. Review example code
4. Check that you're using Python 3.7+
5. Verify your data format is correct

---

## Quick Reference

### Installation
```bash
# Windows
Double-click install.bat

# Linux/Mac
./install.sh
```

### Run Analysis
```bash
python run_nmr_analysis.py
```

### Test Package
```bash
python test_package.py
```

### Run Examples
```bash
python examples/simple_example.py
```

---

## Next Steps

1. ✅ **Install the package** (if you haven't already)
2. ✅ **Run the test script** to verify installation
3. ✅ **Try the example** with synthetic data
4. ✅ **Process your own data** using interactive mode
5. ✅ **Explore the results** in the output directory

---

**Happy analyzing! 🧪**

For more detailed information, see:
- `README.md` - Complete package overview
- `USER_GUIDE.md` - Detailed usage guide
- `QUICKSTART.md` - Quick 5-minute guide


