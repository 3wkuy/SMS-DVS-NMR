#!/usr/bin/env python3
"""
Main execution script for CPMG NMR Data Analysis
This script provides a user-friendly interface for running the NMR analysis
"""

import sys
import os
from pathlib import Path

# Add current directory to path to import the module
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

try:
    from nmr_cpmg_analysis import main
    print("✓ Successfully loaded CPMG NMR Analysis module")
    print()
except ImportError as e:
    print(f"ERROR: Could not import the analysis module: {e}")
    print()
    print("Please ensure:")
    print("1. You have installed all dependencies: pip install -r requirements.txt")
    print("2. The file 'merged_CPMG_ILT_analysis_v1.3.py' is in the 'nmr_cpmg_analysis' directory")
    print("3. Python 3.7 or higher is installed")
    sys.exit(1)

if __name__ == "__main__":
    print("="*60)
    print("CPMG NMR Data Processing with ILT Analysis")
    print("="*60)
    print()
    print("This program will guide you through processing your NMR data.")
    print()
    
    # Run the main analysis function
    try:
        main()
        print()
        print("="*60)
        print("Analysis completed!")
        print("="*60)
    except KeyboardInterrupt:
        print()
        print()
        print("Analysis interrupted by user.")
    except Exception as e:
        print()
        print("="*60)
        print(f"ERROR: {e}")
        print("="*60)
        print()
        import traceback
        traceback.print_exc()
        print()
        print("Please check:")
        print("1. Your data files exist and are accessible")
        print("2. The file paths are correct")
        print("3. You have sufficient permissions to read/write files")
        print()
        sys.exit(1)

