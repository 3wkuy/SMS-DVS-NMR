"""
CPMG NMR Data Processing Package

A comprehensive package for processing CPMG NMR data with Inverse Laplace Transform (ILT) analysis.

Main functions:
- perform_ilt: Perform ILT using RMEA1D or ITAMeD method
- rmea1d: Regularized multi-exponential analysis
- find_optimal_lambda: Find optimal regularization parameter
- main: Main processing function for batch analysis

Usage:
    from nmr_cpmg_analysis import perform_ilt, main

    # Run full analysis
    main()

    # Or use individual functions
    f, mc = perform_ilt(t, m, tau, lambda_value)
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

# Import useful utility functions
from .merged_CPMG_ILT_analysis_v1_3 import (
    parse_value,
    load_timestamps_from_csv,
    generate_file_numbers,
    build_processing_plan,
    truncate_dataset,
)

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
    "parse_value",
    "load_timestamps_from_csv",
    "generate_file_numbers",
    "build_processing_plan",
    "truncate_dataset",
]

