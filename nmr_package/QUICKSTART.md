# Quick Start Guide

## Step 1: Download and Extract

1. Download the package
2. Extract to any location (e.g., `C:\Users\YourName\nmr-package\`)

## Step 2: Install Dependencies

### Windows (Recommended)
- **Double-click** `install.bat`
- Wait for installation to complete

### Linux/Mac
- Open terminal in the package directory
- Run: `chmod +x install.sh && ./install.sh`

## Step 3: Run Analysis

```bash
python run_nmr_analysis.py
```

or on Linux/Mac:
```bash
python3 run_nmr_analysis.py
```

**Optional:** For advanced ITAMeD features, see `ITAMED_INSTALLATION.md`

## What to Expect

1. The script will show available datasets (1-10)
2. Select a number or choose custom (0)
3. Confirm file range or modify it
4. Wait for processing (may take several minutes)
5. Results will be saved in your data directory

## Common Issues

### "Python not found"
- Download Python from https://www.python.org/downloads/
- Install Python 3.7 or higher
- Make sure to check "Add Python to PATH" during installation

### "Module not found" errors
- Run `pip install -r requirements.txt`
- Make sure you're in the package directory

### "ITAMeD module not available"
- This is a WARNING, not an error
- RMEA1D method works perfectly without ITAMeD
- For advanced features, see `ITAMED_INSTALLATION.md`

### Can't find your data
- Use absolute paths (e.g., `E:/SMS-NMR/Data/...`)
- Check that files exist and are readable
- On Windows, use forward slashes (/) instead of backslashes (\)

## Need More Help?

See `README.md` for detailed documentation.

