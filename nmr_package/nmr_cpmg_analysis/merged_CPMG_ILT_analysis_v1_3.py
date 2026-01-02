#!/usr/bin/env python3

"""
CPMG NMR Data Processing Script with Advanced ILT Analysis

This script processes CPMG NMR data from TNMR software, performs T2 fitting,
and applies Inverse Laplace Transform (ILT) analysis with automatic lambda optimization.
"""

import sys
import time
import os
import argparse
import subprocess
import re
import numpy as np
import win32com.client
import matplotlib.pyplot as plt
from scipy.signal import find_peaks
from scipy.optimize import nnls
import xml.etree.ElementTree as ET
import pandas as pd
from pathlib import Path

# Try to import ITAMeD
ITAMED_AVAILABLE = False
ITAMED_L2_AVAILABLE = False
itamed = None

# First, try to import from bundled external_packages
try:
    # Get the package directory (parent of nmr_cpmg_analysis)
    package_dir = Path(__file__).parent.parent
    external_packages_dir = package_dir / "external_packages"
    if external_packages_dir.exists():
        external_packages_path = str(external_packages_dir)
        if external_packages_path not in sys.path:
            sys.path.insert(0, external_packages_path)
    
    # Try to import from bundled packages
    from external_packages.processing import core as itamed  # type: ignore
    if hasattr(itamed, 'itamed1d'):
        ITAMED_AVAILABLE = True
        print("[OK] ITAMeD module available (bundled)")
    else:
        print("[WARNING] ITAMeD module imported but itamed1d function not found")
        itamed = None
except ImportError:
    # Fallback: Try to import from ITAMeD_python directory if it exists
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
            print("[OK] ITAMeD module available (from ITAMeD_python directory)")
        else:
            print("[WARNING] ITAMeD module imported but itamed1d function not found")
            itamed = None
    except ImportError:
        print("[WARNING] ITAMeD module not available - only RMEA1D method will be available")
        itamed = None  # Set to None to avoid errors

# Try to import L2 version (for non-sparse data with broad peaks)
ITAMED_L2_AVAILABLE = False
itamed_l2 = None

# First, try to import from bundled external_packages
try:
    # Get the package directory (parent of nmr_cpmg_analysis)
    package_dir = Path(__file__).parent.parent
    external_packages_dir = package_dir / "external_packages"
    
    # Check if source .py file exists
    l2_module_path = external_packages_dir / "itamed_l2_version.py"
    if l2_module_path.exists():
        # Try to import directly from external_packages module
        import external_packages.itamed_l2_version as itamed_l2  # type: ignore
        if hasattr(itamed_l2, 'itamed1d_l2'):
            ITAMED_L2_AVAILABLE = True
            print("[OK] ITAMeD L2 version available (for smooth, broad peaks) - bundled")
        else:
            print("[WARNING] ITAMeD L2 module imported but itamed1d_l2 function not found")
            itamed_l2 = None
    else:
        # Try loading from .pyc file if .py doesn't exist
        l2_pyc_path = external_packages_dir / "itamed_l2_version.cpython-312.pyc"
        if l2_pyc_path.exists():
            print("[WARNING] ITAMeD L2 version found as compiled .pyc file - source .py file needed for proper import")
            print("[WARNING] ITAMeD L2 version not found - will use L1 (sparse) regularization")
        else:
            print("[WARNING] ITAMeD L2 version not found - will use L1 (sparse) regularization")
except (ImportError, AttributeError) as e:
    # Fallback: Try to import from external_packages directory directly using importlib
    try:
        if 'external_packages_dir' in locals() and external_packages_dir.exists():
            l2_module_path = external_packages_dir / "itamed_l2_version.py"
            if l2_module_path.exists():
                import importlib.util
                spec = importlib.util.spec_from_file_location("itamed_l2_version", l2_module_path)
                itamed_l2 = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(itamed_l2)
                if hasattr(itamed_l2, 'itamed1d_l2'):
                    ITAMED_L2_AVAILABLE = True
                    print("[OK] ITAMeD L2 version available (for smooth, broad peaks) - loaded from file")
                else:
                    print("[WARNING] ITAMeD L2 module found but itamed1d_l2 function not available")
                    itamed_l2 = None
    except Exception as e2:
        print(f"[WARNING] Could not load ITAMeD L2 version: {e2}")
        print("  Will use L1 (sparse) regularization if ITAMeD is selected")
        itamed_l2 = None
except Exception as e:
    print(f"[WARNING] Could not load ITAMeD L2 version: {e}")
    print("  Will use L1 (sparse) regularization if ITAMeD is selected")
    itamed_l2 = None

# ITAMeD Regularization type (defaults to L2 for better match to broad peaks)
ITAMED_REGULARIZATION = "L2"  # Options: "L1" or "L2"


######################## ILT Method Wrapper Function ###########################

def perform_ilt(t, m, tau, lambda_value, method='rmea1d', niter=10000):
    """
    Wrapper function to perform ILT using either RMEA1D or ITAMeD method.
    
    Parameters:
    -----------
    t : array-like
        Time points
    m : array-like
        Signal measurements at discrete time points
    tau : array-like
        Time constants for the distribution
    lambda_value : float
        Regularization parameter
    method : str
        'rmea1d' or 'itamed'
    niter : int
        Number of iterations for ITAMeD (default: 10000)
    
    Returns:
    --------
    f : array
        Amplitudes corresponding to time constants tau
    mc : array
        Computed signal at discrete time points
    """
    # Normalize method string to lowercase for consistent comparison
    method = method.lower().strip() if isinstance(method, str) else 'rmea1d'
    
    if method == 'itamed':
        if not ITAMED_AVAILABLE or itamed is None:
            raise ImportError("ITAMeD module not available. Please install ITAMeD_python or use 'rmea1d' method.")
        
        # DEBUG: Confirm ITAMeD is being used
        print(f"    [DEBUG] perform_ilt: Using ITAMeD method (lambda={lambda_value:.2e})")
        
        # Convert tau array to tau_range format [min, max, n_points]
        tau_min = np.min(tau)
        tau_max = np.max(tau)
        tau_npoints = len(tau)
        tau_range = [tau_min, tau_max, tau_npoints]
        
        # ITAMeD expects time in same units as tau (ms), signal as array
        t_array = np.array(t)
        m_array = np.array(m)
        
        # Use L2 regularization for smooth, broad peaks (better match to experimental data)
        # Fallback to L1 if L2 not available (for old ITAMeD packages)
        regularization = ITAMED_REGULARIZATION.upper() if ITAMED_REGULARIZATION else 'L2'
        
        try:
            if regularization == 'L2' and ITAMED_L2_AVAILABLE and itamed_l2 is not None:
                # Use L2 regularization (smooth, broad peaks)
                print(f"    [DEBUG] perform_ilt: Calling ITAMeD L2 (itamed_l2.itamed1d_l2)")
                d_scale, out_array = itamed_l2.itamed1d_l2(niter, tau_range, m_array, t_array, lambda_value, 'T2', regularization='L2')
                print(f"    [DEBUG] perform_ilt: ITAMeD L2 completed - output shape: {np.array(out_array).shape}")
            else:
                # Use L1 regularization (sparse, sharp peaks) - original ITAMeD
                if regularization == 'L2' and not ITAMED_L2_AVAILABLE:
                    print(f"  [INFO] L2 regularization requested but not available, using L1 (sparse)")
                print(f"    [DEBUG] perform_ilt: Calling ITAMeD L1 (itamed.itamed1d)")
                d_scale, out_array = itamed.itamed1d(niter, tau_range, m_array, t_array, lambda_value, 'T2')
                print(f"    [DEBUG] perform_ilt: ITAMeD L1 completed - output shape: {np.array(out_array).shape}")
        except Exception as e:
            print(f"    [ERROR] ITAMeD failed with error: {e}")
            print(f"    [ERROR] Falling back to RMEA1D")
            import traceback
            traceback.print_exc()
            # Fallback to RMEA1D if ITAMeD fails
            return rmea1d(t, m, tau, lambda_value)
        
        # ITAMeD returns distribution as column vector, convert to 1D array
        if out_array.ndim > 1:
            f = np.array(out_array).ravel()
        else:
            f = np.array(out_array)
        
        # Compute fitted signal: mc = A @ f
        A = np.exp(-np.outer(t_array, 1.0 / d_scale))
        mc = A @ f
        
        print(f"    [DEBUG] perform_ilt: ITAMeD result - f shape: {f.shape}, f max: {np.max(f):.6e}, mc shape: {mc.shape}")
        
        return f, mc
    else:  # rmea1d (default)
        print(f"    [DEBUG] perform_ilt: Using RMEA1D method (lambda={lambda_value:.2e})")
        f, mc = rmea1d(t, m, tau, lambda_value)
        print(f"    [DEBUG] perform_ilt: RMEA1D result - f shape: {f.shape}, f max: {np.max(f):.6e}, mc shape: {mc.shape}")
        return f, mc


######################## Multi-Exponential Analysis Function ###########################

def rmea1d(t, m, tau, lambda_value):
    """
    RMEA1D Performs 1D regularized multi-exponential analysis on experimental data.
    
    Parameters:
    -----------
    t : array-like
        Time points
    m : array-like
        Signal measurements at discrete time points
    tau : array-like
        Time constants for the distribution
    lambda_value : float
        Regularization parameter
    
    Returns:
    --------
    f : array
        Amplitudes corresponding to time constants tau
    mc : array
        Computed signal at discrete time points
    """
    A = np.exp(-np.outer(t, 1.0 / tau))
    C = np.vstack((A, lambda_value * np.eye(A.shape[1])))
    p = np.hstack((m, np.zeros(A.shape[1])))
    x = nnls(C, p)[0]
    mc = A @ x
    f = x
    return (f, mc)


######################## L-Curve Optimization Function ###########################

def compute_lcurve_rmea(time_ms, signal, tau_ms, lambda_values, method='rmea1d'):
    """
    Evaluate residual and solution norms for ILT across a λ grid using RMEA1D (fast).
    Uses L2 norm (Euclidean norm) for both residual and solution norms.
    
    Parameters:
    -----------
    time_ms : array-like
        Time points in milliseconds
    signal : array-like
        Signal measurements at discrete time points
    tau_ms : array-like
        Time constants for the distribution
    lambda_values : array-like
        Array of lambda values to test
    method : str
        'rmea1d' or 'itamed' (default: 'rmea1d' for speed)
    
    Returns:
    --------
    residual_norms : array
        L2 residual norms ||A·f - m||₂ for each lambda value
    solution_norms : array
        L2 solution norms ||f||₂ for each lambda value
    curves : list
        List of tuples (f, mc) for each lambda value
    """
    residuals = []
    solutions = []
    curves = []
    
    # For lambda optimization, use rmea1d for speed (as in notebook)
    # Final ILT will use selected method
    optimization_method = 'rmea1d' if method == 'itamed' else method
    
    for lam in lambda_values:
        f_tmp, mc_tmp = perform_ilt(time_ms, signal, tau_ms, lam, method=optimization_method)
        # Explicitly use L2 norm (ord=2) for both residual and solution norms
        residuals.append(np.linalg.norm(mc_tmp - signal, ord=2))
        solutions.append(np.linalg.norm(f_tmp, ord=2))
        curves.append((f_tmp, mc_tmp))
    
    return np.array(residuals), np.array(solutions), curves


def compute_lcurve_itamed(time_ms, signal, tau_ms, lambda_values, niter=10000):
    """
    Evaluate residual and solution norms for ILT across a λ grid using ITAMeD itself.
    This matches the reference notebook approach where ITAMeD is used for lambda optimization.
    Uses L2 norm (Euclidean norm) for both residual and solution norms.
    
    Parameters:
    -----------
    time_ms : array-like
        Time points in milliseconds
    signal : array-like
        Signal measurements at discrete time points
    tau_ms : array-like
        Time constants for the distribution
    lambda_values : array-like
        Array of lambda values to test
    niter : int
        Number of iterations for ITAMeD (default: 10000)
    
    Returns:
    --------
    residual_norms : array
        L2 residual norms ||A·f - m||₂ for each lambda value
    solution_norms : array
        L2 solution norms ||f||₂ for each lambda value
    curves : list
        List of tuples (f, mc) for each lambda value
    """
    if not ITAMED_AVAILABLE or itamed is None:
        raise ImportError("ITAMeD module not available. Please install ITAMeD_python or use 'rmea1d' method.")
    
    residuals = []
    solutions = []
    curves = []
    
    # Convert tau array to tau_range format [min, max, n_points]
    tau_min = np.min(tau_ms)
    tau_max = np.max(tau_ms)
    tau_npoints = len(tau_ms)
    tau_range = [tau_min, tau_max, tau_npoints]
    
    # Convert inputs to numpy arrays
    t_array = np.array(time_ms)
    m_array = np.array(signal)
    
    print(f"  Computing L-curve using ITAMeD (this may take longer than RMEA1D)...")
    
    # Use L2 regularization for ITAMeD (better match to broad peaks)
    # Fallback to L1 if L2 not available (for old ITAMeD packages)
    regularization = ITAMED_REGULARIZATION.upper() if ITAMED_REGULARIZATION else 'L2'
    
    for lam in lambda_values:
        # Call ITAMeD with L2 regularization if available, otherwise L1
        if regularization == 'L2' and ITAMED_L2_AVAILABLE and itamed_l2 is not None:
            d_scale, out_array = itamed_l2.itamed1d_l2(niter, tau_range, m_array, t_array, lam, 'T2', regularization='L2')
        else:
            d_scale, out_array = itamed.itamed1d(niter, tau_range, m_array, t_array, lam, 'T2')
        
        # ITAMeD returns distribution as column vector, convert to 1D array
        if out_array.ndim > 1:
            f_tmp = np.array(out_array).ravel()
        else:
            f_tmp = np.array(out_array)
        
        # Compute fitted signal: mc = A @ f
        A = np.exp(-np.outer(t_array, 1.0 / d_scale))
        mc_tmp = A @ f_tmp
        
        # Explicitly use L2 norm (ord=2) for both residual and solution norms
        residuals.append(np.linalg.norm(mc_tmp - signal, ord=2))
        solutions.append(np.linalg.norm(f_tmp, ord=2))
        curves.append((f_tmp, mc_tmp))
    
    return np.array(residuals), np.array(solutions), curves


def choose_lambda_balanced(lambda_values, residual_norms, solution_norms):
    """
    Select λ using a weighted product heuristic biased towards mid-range values.
    
    Parameters:
    -----------
    lambda_values : array-like
        Array of lambda values tested
    residual_norms : array-like
        Residual norms for each lambda value
    solution_norms : array-like
        Solution norms for each lambda value
    
    Returns:
    --------
    optimal_idx : int
        Index of the optimal lambda value
    """
    products = residual_norms * solution_norms
    weights = np.ones_like(products)
    
    for idx, lam in enumerate(lambda_values):
        log_lam = np.log10(lam)
        if log_lam > 1.0:
            weights[idx] = 0.1
        elif log_lam > 0.7:
            weights[idx] = 0.3
        elif log_lam < -1.0:
            weights[idx] = 0.2
        elif -0.5 <= log_lam <= 0.7:
            weights[idx] = 5.0
        elif -1.0 <= log_lam <= 1.0:
            weights[idx] = 2.0
    
    weighted_products = products / weights
    tol = 1e-6
    finite_mask = solution_norms > tol
    if np.any(finite_mask):
        weighted_products = np.where(finite_mask, weighted_products, np.inf)
        return int(np.argmin(weighted_products))
    
    return int(np.argmin(products))


def find_optimal_lambda(t, m, tau, label='', save_dir=None, method='rmea1d', lambda_opt_method=None):
    """
    Find optimal lambda using the balanced product minimization method.
    All norm calculations use L2 norm (Euclidean norm): ||A·f - m||₂ and ||f||₂.
    
    Parameters:
    -----------
    t : array-like
        Time points
    m : array-like
        Signal measurements at discrete time points
    tau : array-like
        Time constants for the distribution
    label : str
        Label for the plot title
    save_dir : str
        Directory to save the L-curve plot
    method : str
        'rmea1d' or 'itamed' - method to use for final ILT
    lambda_opt_method : str, optional
        If None, automatically uses same method as 'method' parameter.
        For ITAMeD, MUST use ITAMeD for lambda optimization (cannot use RMEA).
        For RMEA1D, uses RMEA1D for lambda optimization.
    
    Returns:
    --------
    optimal_lambda : float
        The optimal regularization parameter
    """
    # CRITICAL: ITAMeD MUST use ITAMeD for lambda optimization (they use different ILT approaches)
    # RMEA lambda values are not compatible with ITAMeD
    if method == 'itamed':
        if lambda_opt_method is not None and lambda_opt_method != 'itamed':
            print(f"  [WARNING] ITAMeD method requires ITAMeD for lambda optimization.")
            print(f"  [WARNING] Ignoring lambda_opt_method='{lambda_opt_method}', using 'itamed' instead.")
        lambda_opt_method = 'itamed'
    elif method == 'rmea1d':
        lambda_opt_method = 'rmea1d'
    else:
        raise ValueError(f"Unknown method: {method}")
    
    # Range of lambda values to test (logarithmically spaced)
    # ITAMeD typically needs smaller lambda values than RMEA
    if lambda_opt_method == 'itamed':
        lambda_values = np.logspace(-3, 1, 50)  # ITAMeD range: 0.001 to 10
    else:
        lambda_values = np.logspace(-4, 2, 50)  # RMEA range: 0.0001 to 100
    
    # Compute L-curve data using selected lambda optimization method
    if lambda_opt_method == 'itamed':
        residual_norms, solution_norms, curves = compute_lcurve_itamed(t, m, tau, lambda_values)
        opt_method_label = 'ITAMeD'
    else:
        residual_norms, solution_norms, curves = compute_lcurve_rmea(t, m, tau, lambda_values, method='rmea1d')
        opt_method_label = 'RMEA1D'
    
    # Select optimal lambda using balanced product minimization
    optimal_idx = choose_lambda_balanced(lambda_values, residual_norms, solution_norms)
    lambda_selected = lambda_values[optimal_idx]
    
    # Apply the new optimal lambda: divide selected lambda by 3 only for RMEA1D
    # ITAMeD doesn't need this adjustment (matches reference notebook approach)
    if lambda_opt_method == 'itamed':
        optimal_lambda = lambda_selected
        lambda_adjustment_note = ""
    else:
        optimal_lambda = lambda_selected / 3.0
        lambda_adjustment_note = " (λ/3)"
    
    # Debug output
    print(f"  Lambda optimization: Balanced product minimization method selected")
    print(f"  Lambda optimization method: {opt_method_label}")
    print(f"  Using L2 norm (||·||₂) for all residual and solution norm calculations")
    print(f"  Selected lambda from grid: {lambda_selected:.2e} (index {optimal_idx})")
    if lambda_opt_method == 'itamed':
        print(f"  Final optimal lambda: {optimal_lambda:.2e} (no adjustment)")
    else:
        print(f"  Final optimal lambda{lambda_adjustment_note}: {optimal_lambda:.2e}")
    
    # Plot L-curve
    plt.figure(figsize=(14, 6))
    
    # Main L-curve
    plt.subplot(1, 2, 1)
    plt.loglog(residual_norms, solution_norms, 'b-o', linewidth=2, markersize=4, 
               label=f'L-curve ({opt_method_label})')
    plt.loglog(residual_norms[optimal_idx], solution_norms[optimal_idx],
               'r*', markersize=15, label=f'Selected λ = {lambda_selected:.2e}')
    
    # Compute residual and solution norms for the actual optimal lambda (which may not be in grid)
    # Use the same method as lambda optimization for consistency
    # Explicitly use L2 norm (ord=2) for both residual and solution norms
    f_opt, mc_opt = perform_ilt(t, m, tau, optimal_lambda, method=lambda_opt_method)
    opt_residual = np.linalg.norm(mc_opt - m, ord=2)
    opt_solution = np.linalg.norm(f_opt, ord=2)
    optimal_label = f'Optimal λ* = {optimal_lambda:.2e}{lambda_adjustment_note}'
    plt.loglog(opt_residual, opt_solution, 'g*', markersize=15, label=optimal_label)
    
    plt.xlabel('Residual Norm ||A·f - m||₂', fontsize=10)
    plt.ylabel('Solution Norm ||f||₂', fontsize=10)
    plt.title(f'L-Curve for {label} (λ optimization: {opt_method_label})', fontsize=12, fontweight='bold')
    plt.legend(fontsize=8)
    plt.grid(True, which='both', linestyle='--', alpha=0.6)
    
    # Show lambda values
    plt.subplot(1, 2, 2)
    plt.semilogx(lambda_values, residual_norms, 'b-o', linewidth=2, markersize=4, label='Residual Norm')
    plt.semilogx(lambda_values, solution_norms, 'g-o', linewidth=2, markersize=4, label='Solution Norm')
    plt.axvline(x=lambda_selected, color='r', linestyle='--', linewidth=2, 
                label=f'Selected λ = {lambda_selected:.2e}')
    plt.axvline(x=optimal_lambda, color='g', linestyle='--', linewidth=2, 
                label=f'Optimal λ* = {optimal_lambda:.2e}{lambda_adjustment_note}')
    plt.xlabel('Lambda (λ)', fontsize=10)
    plt.ylabel('Norm', fontsize=10)
    plt.title('Norms vs Lambda', fontsize=12)
    plt.legend(fontsize=8)
    plt.grid(True, which='both', linestyle='--', alpha=0.6)
    
    plt.tight_layout()
    
    # Save the L-curve plot in method-specific plots subfolder
    # Use same format as other plots: plots/{ilt_method}_{lambda_opt_method}/
    label_clean = label.replace(" ", "_").replace("(", "").replace(")", "")
    if save_dir is None:
        save_dir = os.getcwd()
    # Create method-specific plots subfolder matching Step 4 format
    method_subfolder = f"{method}_{lambda_opt_method}"
    plots_subdir = os.path.join(save_dir, "plots", method_subfolder)
    os.makedirs(plots_subdir, exist_ok=True)
    save_path = os.path.join(plots_subdir, f"L_curve_{label_clean}.jpg")
    plt.savefig(save_path, dpi=300, bbox_inches="tight")
    print(f"  L-curve plot saved: {save_path}")
    plt.close()
    
    print(f"  Optimal lambda for {label}: {optimal_lambda:.2e}")
    
    return optimal_lambda


######################## Peak Area Analysis Function ###########################

def analyze_peak_integrals(final_results, tau, save_dir=None):
    """
    Analyze T2 distribution peaks and calculate areas under the curve for short and long T2 components.
    
    This function:
    1. Detects two major peaks in each T2 distribution using dynamic peak detection
    2. Finds the valley (local minimum) between the peaks as the separation boundary
    3. Calculates the area under the curve (AUC) for short T2 peak (start to valley) and long T2 peak (valley to end)
    4. Plots the peak areas vs time
    
    Parameters:
    -----------
    final_results : list
        List of dictionaries, each containing:
        - 'f': T2 distribution amplitudes (array)
        - 'tau': T2 relaxation times (array) - optional, uses global tau if not present
        - 'time_minutes': Time in minutes for x-axis
        - 'time_seconds': Time in seconds (optional)
        - 'label': Label for the dataset
    tau : array-like
        T2 relaxation times (x-axis values) in milliseconds
    save_dir : str, optional
        Directory to save the peak areas plot. If None, uses plots_dir from final_results[0]['fd']
    
    Returns:
    --------
    dict : Dictionary containing:
        - 'time_minutes': Array of time values in minutes
        - 'short_t2_areas': Array of short T2 peak areas
        - 'long_t2_areas': Array of long T2 peak areas
        - 'valley_indices': Array of valley indices for each distribution
        - 'peak1_indices': Array of first peak indices
        - 'peak2_indices': Array of second peak indices
    """
    print("\n" + "="*80)
    print("STEP 8: ANALYZING PEAK INTEGRALS")
    print("="*80)
    
    # Determine save directory
    if save_dir is None:
        if len(final_results) > 0:
            save_dir = os.path.join(final_results[0].get('fd', os.getcwd()), "plots")
        else:
            save_dir = os.path.join(os.getcwd(), "plots")
    
    # Ensure save directory exists
    os.makedirs(save_dir, exist_ok=True)
    
    # Convert tau to numpy array if needed
    tau = np.array(tau)
    
    # Storage for results
    time_minutes_list = []
    short_t2_areas = []
    long_t2_areas = []
    valley_indices = []
    peak1_indices = []
    peak2_indices = []
    
    print(f"Analyzing {len(final_results)} datasets for peak separation and integration...")
    
    for idx, result in enumerate(final_results):
        # Get T2 distribution
        f = result['f']
        label = result.get('label', f'Dataset {idx+1}')
        
        # Get time information (prefer time_minutes, fallback to time_seconds/60)
        if 'time_minutes' in result:
            time_min = result['time_minutes']
        elif 'time_seconds' in result:
            time_min = result['time_seconds'] / 60.0
        else:
            # Fallback: use index as time (assuming sequential measurements)
            time_min = idx * 412 / 60.0  # 412 seconds per experiment
        
        # Use tau from result if available, otherwise use global tau
        tau_local = np.array(result.get('tau', tau))
        
        # Ensure tau_local and f have the same length
        if len(tau_local) != len(f):
            print(f"  [WARNING] {label}: tau length ({len(tau_local)}) != f length ({len(f)}), using global tau")
            tau_local = tau[:len(f)]
        
        # Dynamic peak detection
        # Find peaks in the T2 distribution
        # Use a minimum height threshold (e.g., 10% of max) to avoid noise
        max_amplitude = np.max(f)
        min_height = max_amplitude * 0.1
        
        # Find all peaks
        peaks, properties = find_peaks(f, height=min_height, distance=len(f)//20)
        
        if len(peaks) < 2:
            # If less than 2 peaks found, try with lower threshold
            min_height = max_amplitude * 0.05
            peaks, properties = find_peaks(f, height=min_height, distance=len(f)//30)
        
        if len(peaks) >= 2:
            # Sort peaks by amplitude (descending) to get the two largest peaks
            peak_amplitudes = f[peaks]
            sorted_indices = np.argsort(peak_amplitudes)[::-1]
            top_two_peaks = peaks[sorted_indices[:2]]
            top_two_peaks = np.sort(top_two_peaks)  # Sort by position (T2 time)
            
            peak1_idx = top_two_peaks[0]
            peak2_idx = top_two_peaks[1]
            
            # Find valley (local minimum) between the two peaks
            valley_region = f[peak1_idx:peak2_idx+1]
            valley_local_idx = np.argmin(valley_region)
            valley_idx = peak1_idx + valley_local_idx
            
            # Ensure valley is between peaks
            if valley_idx <= peak1_idx:
                valley_idx = peak1_idx + 1
            if valley_idx >= peak2_idx:
                valley_idx = peak2_idx - 1
            
        elif len(peaks) == 1:
            # Only one peak found - use midpoint as valley
            peak1_idx = peaks[0]
            peak2_idx = len(f) - 1
            valley_idx = (peak1_idx + peak2_idx) // 2
            print(f"  [WARNING] {label}: Only 1 peak detected, using midpoint as valley")
            
        else:
            # No peaks found - use midpoint as separation
            peak1_idx = 0
            peak2_idx = len(f) - 1
            valley_idx = (peak1_idx + peak2_idx) // 2
            print(f"  [WARNING] {label}: No peaks detected, using midpoint as separation")
        
        # Enforce 200ms hard limit on valley point
        valley_tau_value = tau_local[valley_idx]
        original_valley_idx = valley_idx
        if valley_tau_value > 200.0:
            # Find the index in tau_local that is closest to 200ms
            tau_diff = np.abs(tau_local - 200.0)
            valley_idx = np.argmin(tau_diff)
            # Ensure valley_idx is valid (within bounds)
            valley_idx = min(valley_idx, len(tau_local) - 1)
            valley_idx = max(valley_idx, 0)
            print(f"  [INFO] {label}: Valley point clamped to 200ms limit (original: {valley_tau_value:.2f} ms at index {original_valley_idx}, new: {tau_local[valley_idx]:.2f} ms at index {valley_idx})")
        
        # Calculate areas using trapezoidal integration
        # Short T2 peak: from start to valley
        short_t2_f = f[:valley_idx+1]
        short_t2_tau = tau_local[:valley_idx+1]
        short_area = np.trapz(y=short_t2_f, x=short_t2_tau)
        
        # Long T2 peak: from valley to end
        long_t2_f = f[valley_idx:]
        long_t2_tau = tau_local[valley_idx:]
        long_area = np.trapz(y=long_t2_f, x=long_t2_tau)
        
        # Store results
        time_minutes_list.append(time_min)
        short_t2_areas.append(short_area)
        long_t2_areas.append(long_area)
        valley_indices.append(valley_idx)
        peak1_indices.append(peak1_idx)
        peak2_indices.append(peak2_idx)
        
        if idx < 3 or idx >= len(final_results) - 3:
            print(f"  {label}: Short T2 area = {short_area:.6e}, Long T2 area = {long_area:.6e}, "
                  f"Valley at tau[{valley_idx}] = {tau_local[valley_idx]:.2f} ms")
    
    # Convert to numpy arrays
    time_minutes_array = np.array(time_minutes_list)
    short_t2_areas_array = np.array(short_t2_areas)
    long_t2_areas_array = np.array(long_t2_areas)
    
    # Extract signal intensities for all results
    signal_intensities = []
    for result in final_results:
        signal_int = result.get('signal_intensity', result.get('signal_intensity_raw', 0.0))
        signal_intensities.append(signal_int)
    signal_intensities_array = np.array(signal_intensities)
    
    # Calculate scaling factor to match Total Signal Intensity max to Short T2 Area max
    # This makes the signal intensity visible on the same scale
    max_short = np.max(np.abs(short_t2_areas_array))
    max_signal = np.max(np.abs(signal_intensities_array)) if len(signal_intensities_array) > 0 and np.max(np.abs(signal_intensities_array)) > 0 else 1.0
    scaling_factor = max_short / max_signal if max_signal > 0 else 1.0
    signal_intensities_scaled = signal_intensities_array * scaling_factor
    
    print(f"\nSignal Intensity Scaling:")
    print(f"  Max Short T2 Area: {max_short:.6e}")
    print(f"  Max Signal Intensity (raw): {max_signal:.6e}")
    print(f"  Scaling Factor: {scaling_factor:.6e}")
    print(f"  Max Signal Intensity (scaled): {np.max(signal_intensities_scaled):.6e}")
    
    # Create plot
    print("\nGenerating peak areas vs time plot...")
    
    # Check if areas have vastly different magnitudes (more than 10x difference)
    max_long = np.max(np.abs(long_t2_areas_array))
    use_dual_axis = (max_short > 0 and max_long > 0 and 
                     (max_short / max_long > 10 or max_long / max_short > 10))
    
    if use_dual_axis:
        # Use dual y-axis if magnitudes are very different
        fig, ax1 = plt.subplots(figsize=(12, 6))
        
        # Plot short T2 area on left y-axis
        color1 = 'tab:blue'
        ax1.set_xlabel('Time (minutes)', fontsize=12)
        ax1.set_ylabel('Short T2 Peak Area', color=color1, fontsize=12)
        line1 = ax1.plot(time_minutes_array, short_t2_areas_array, 'o-', 
                        color=color1, linewidth=2, markersize=6, label='Short T2 Area')
        ax1.tick_params(axis='y', labelcolor=color1)
        ax1.grid(True, alpha=0.3)
        
        # Plot scaled signal intensity on left y-axis (green solid line with diamond markers)
        color3 = 'tab:green'
        line3 = ax1.plot(time_minutes_array, signal_intensities_scaled, 'D-', 
                        color=color3, linewidth=2, markersize=5, label='Total Signal Intensity (Scaled)', alpha=0.6)
        
        # Plot long T2 area on right y-axis
        ax2 = ax1.twinx()
        color2 = 'tab:orange'
        ax2.set_ylabel('Long T2 Peak Area', color=color2, fontsize=12)
        line2 = ax2.plot(time_minutes_array, long_t2_areas_array, 's-', 
                        color=color2, linewidth=2, markersize=6, label='Long T2 Area')
        ax2.tick_params(axis='y', labelcolor=color2)
        
        # Combine legends
        lines = line1 + line3 + line2
        labels = [l.get_label() for l in lines]
        ax1.legend(lines, labels, loc='upper left', fontsize=10)
        
        plt.title('Peak Areas vs Time\n(Short T2, Long T2, and Total Signal Intensity)', 
                 fontsize=14, fontweight='bold')
        
    else:
        # Use single y-axis if magnitudes are similar
        fig, ax = plt.subplots(figsize=(12, 6))
        
        ax.plot(time_minutes_array, short_t2_areas_array, 'o-', 
               color='tab:blue', linewidth=2, markersize=6, label='Short T2 Area', alpha=0.8)
        ax.plot(time_minutes_array, long_t2_areas_array, 's-', 
               color='tab:orange', linewidth=2, markersize=6, label='Long T2 Area', alpha=0.8)
        ax.plot(time_minutes_array, signal_intensities_scaled, 'D-', 
               color='tab:green', linewidth=2, markersize=5, label='Total Signal Intensity (Scaled)', alpha=0.6)
        
        ax.set_xlabel('Time (minutes)', fontsize=12)
        ax.set_ylabel('Peak Area (AUC) / Signal Intensity', fontsize=12)
        ax.set_title('Peak Areas vs Time\n(Short T2, Long T2, and Total Signal Intensity)', 
                    fontsize=14, fontweight='bold')
        ax.legend(fontsize=10, loc='best')
        ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # Save plot
    save_path = os.path.join(save_dir, "Peak_Areas_vs_Time.jpg")
    plt.savefig(save_path, dpi=300, bbox_inches="tight")
    print(f"Peak areas plot saved: {save_path}")
    plt.close()
    
    # Print summary statistics
    print("\nPeak area analysis complete!")
    print(f"  Total datasets analyzed: {len(final_results)}")
    print(f"  Short T2 area range: {np.min(short_t2_areas_array):.6e} to {np.max(short_t2_areas_array):.6e}")
    print(f"  Long T2 area range: {np.min(long_t2_areas_array):.6e} to {np.max(long_t2_areas_array):.6e}")
    print(f"  Average Short T2 area: {np.mean(short_t2_areas_array):.6e}")
    print(f"  Average Long T2 area: {np.mean(long_t2_areas_array):.6e}")
    
    return {
        'time_minutes': time_minutes_array,
        'short_t2_areas': short_t2_areas_array,
        'long_t2_areas': long_t2_areas_array,
        'valley_indices': np.array(valley_indices),
        'peak1_indices': np.array(peak1_indices),
        'peak2_indices': np.array(peak2_indices)
    }


######################## Integration Verification Plot Function ###########################

def plot_integration_verification(final_results, tau, peak_area_results, save_dir=None):
    """
    Create a stacked waterfall plot showing the valley finding logic for peak integration.
    
    This function visualizes where the code splits each T2 distribution into Short T2 and Long T2
    components by shading the regions and marking the valley position.
    
    Parameters:
    -----------
    final_results : list
        List of dictionaries, each containing:
        - 'f': T2 distribution amplitudes (array)
        - 'label': Label for the dataset
        - 'valley_index': Index of the valley (separation point) in the tau array
    tau : array-like
        T2 relaxation times (x-axis values) in milliseconds
    peak_area_results : dict
        Dictionary containing peak area analysis results with:
        - 'valley_indices': Array of valley indices for each distribution
    save_dir : str, optional
        Directory to save the plot. If None, uses plots_dir from final_results[0]['fd']
    
    Returns:
    --------
    None (saves plot to file)
    """
    print("\n" + "="*80)
    print("STEP 8.5: GENERATING INTEGRATION VERIFICATION PLOT")
    print("="*80)
    
    # Determine save directory
    if save_dir is None:
        if len(final_results) > 0:
            save_dir = os.path.join(final_results[0].get('fd', os.getcwd()), "plots")
        else:
            save_dir = os.path.join(os.getcwd(), "plots")
    
    # Ensure save directory exists
    os.makedirs(save_dir, exist_ok=True)
    
    # Convert tau to numpy array if needed
    tau = np.array(tau)
    
    # Get valley indices from peak_area_results or final_results
    valley_indices = peak_area_results.get('valley_indices', 
                                           [result.get('valley_index', len(tau)//2) for result in final_results])
    valley_indices = np.array(valley_indices)
    
    # Find maximum intensity for offset calculation
    max_intensity = max([np.max(result['f']) for result in final_results])
    
    # Offset factor for stacking (same as Step 6)
    offset_factor = 0.08
    
    # Plot all samples on a single page
    num_samples = len(final_results)
    
    print(f"Generating integration verification plot: {num_samples} samples on single page...")
    
    # Create figure
    fig, ax = plt.subplots(figsize=(14, 10))
    
    # Set x-axis to log scale (required for fill_between to work correctly with log scale)
    ax.set_xscale('log')
    
    # Check if this is Xigo data (for xlim extension)
    is_xigo_data_verification = any(result.get('rfid_phased') is None for result in final_results)
    
    # Colors for shading
    color_short_t2 = 'blue'
    color_long_t2 = 'orange'
    color_valley_marker = 'red'
    
    # Plot each sample
    for idx, result in enumerate(final_results):
        valley_idx = valley_indices[idx]
        
        # Get T2 distribution
        intensity = result['f']
        
        # Determine label: use time in hours for TNMR data, name for Xigo data
        is_tnmr_data = result.get('rfid_phased') is not None
        if is_tnmr_data:
            # TNMR data: use time in hours
            if 'time_minutes' in result:
                time_hours = result['time_minutes'] / 60.0
                label = f"{time_hours:.1f} hrs"
            elif 'time_seconds' in result:
                time_hours = result['time_seconds'] / 3600.0
                label = f"{time_hours:.1f} hrs"
            else:
                # Fallback: use index-based time
                time_hours = idx * 412 / 3600.0  # 412 seconds per experiment
                label = f"{time_hours:.1f} hrs"
        else:
            # Xigo data: use name/label
            label = result.get('label', f'Sample {idx + 1}')
        
        # Calculate vertical offset
        offset = idx * max_intensity * offset_factor
        
        # Split tau and intensity arrays at valley_index
        # Short T2: from start to valley_index (inclusive)
        tau_short = tau[:valley_idx + 1]
        intensity_short = intensity[:valley_idx + 1]
        
        # Long T2: from valley_index to end
        tau_long = tau[valley_idx:]
        intensity_long = intensity[valley_idx:]
        
        # Valley position (tau value at valley_index)
        tau_valley = tau[valley_idx]
        intensity_valley = intensity[valley_idx]
        
        # Shade Short T2 region (Blue)
        ax.fill_between(tau_short, intensity_short + offset, offset,
                       color=color_short_t2, alpha=0.5, label='Short T2' if idx == 0 else '')
        
        # Shade Long T2 region (Orange)
        ax.fill_between(tau_long, intensity_long + offset, offset,
                       color=color_long_t2, alpha=0.5, label='Long T2' if idx == 0 else '')
        
        # Plot the distribution line (black, thin) for better visibility
        ax.semilogx(tau, intensity + offset, 'k-', linewidth=1, alpha=0.7)
        
        # Mark the valley position with a red 'X' marker (use semilogx for log scale compatibility)
        ax.semilogx([tau_valley], [intensity_valley + offset], 'X', 
                   color=color_valley_marker, markersize=10, markeredgewidth=2,
                   label='Valley (split point)' if idx == 0 else '', zorder=10)
        
        # Add sample label as text annotation at the far right of the plot
        # Position label at maximum T2 value (tau[-1]) and baseline (offset)
        tau_max = tau[-1]
        # Increased fontsize for better readability in double-column format
        label_fontsize = 16 if not is_tnmr_data else 16
        ax.text(tau_max, offset, f"  {label}", 
               fontsize=label_fontsize, ha='left', va='center', alpha=0.8, fontweight='bold')
    
    # Set labels and title
    ax.set_xlabel('T₂ Relaxation Time (ms)', fontsize=16)
    ax.set_ylabel('Intensity (a.u.) - Offset for clarity', fontsize=16)
    # Set xlim - labels will be placed at tau[-1], so ensure it's visible
    # Increased extension factors to prevent text overlap with plot box
    # For Xigo data: extend significantly more to accommodate long filenames
    # For TNMR data: increase extension to accommodate time labels
    if is_xigo_data_verification:
        tau_max_plot = tau[-1] * 20  # Extended further for Xigo data (long filenames)
    else:
        tau_max_plot = tau[-1] * 3.5  # Increased extension for TNMR data to accommodate time labels
    ax.set_xlim([1, tau_max_plot])
    
    ax.set_title(
        f'Integration Verification: Valley Finding Logic ({num_samples} samples)\n'
        f'Blue = Short T2 region | Orange = Long T2 region | Red X = Valley (split point)',
        fontsize=18,
        fontweight='bold'
    )
    
    # Add legend with increased font size
    ax.legend(fontsize=14, loc='upper left', framealpha=0.9)
    
    # Increase tick label sizes for better readability in double-column format
    ax.tick_params(axis='both', which='major', labelsize=14)
    ax.tick_params(axis='both', which='minor', labelsize=12)
    
    ax.grid(True, which='both', alpha=0.3)
    
    plt.tight_layout()
    
    # Save plot
    save_path = os.path.join(save_dir, "Integration_Verification_Stacked.jpg")
    plt.savefig(save_path, dpi=300, bbox_inches="tight")
    print(f"  Integration verification plot saved: {save_path}")
    plt.close()
    
    print(f"\nIntegration verification plot complete!")
    print(f"  Total samples visualized: {num_samples}")


######################## Utility Functions ###########################

def parse_value(val, as_int=False):
    """Parse string values to float or int, handling various formats."""
    if isinstance(val, (int, float)):
        return int(val) if as_int else float(val)
    
    num = ''.join(ch for ch in val if (ch.isdigit() or ch == '.'))
    
    return int(float(num)) if as_int else float(num)


def load_timestamps_from_csv(timestamp_file, filename_prefix):
    """
    Load timestamps from CSV file and return a dictionary mapping file numbers to timestamps.
    
    Parameters:
    -----------
    timestamp_file : str
        Path to CSV file with timestamps
    filename_prefix : str
        Prefix of the filename (e.g., 'CPMG_relaxorption_T2_LiCl_')
    
    Returns:
    --------
    dict : Dictionary mapping file_number -> timestamp (datetime object)
    """
    if not os.path.exists(timestamp_file):
        raise FileNotFoundError(f"Timestamp file not found: {timestamp_file}")
    
    # Read CSV file
    df = pd.read_csv(timestamp_file)
    
    # Check required columns
    if 'File Name' not in df.columns or 'Last Modified Time' not in df.columns:
        raise ValueError(f"CSV file must have 'File Name' and 'Last Modified Time' columns. Found: {list(df.columns)}")
    
    # Parse timestamps
    timestamps_dict = {}
    skipped_count = 0
    for _, row in df.iterrows():
        filename = str(row['File Name']).strip()
        timestamp_str = str(row['Last Modified Time']).strip()
        
        # Extract file number from filename (e.g., "CPMG_relaxorption_T2_LiCl_1.tnt" -> 1)
        if filename_prefix in filename:
            # Remove prefix and extension
            file_num_str = filename.replace(filename_prefix, '').replace('.tnt', '').strip()
            try:
                file_num = int(file_num_str)
                # Parse timestamp
                timestamp = pd.to_datetime(timestamp_str)
                timestamps_dict[file_num] = timestamp
            except (ValueError, KeyError) as e:
                print(f"  WARNING: Could not parse file number or timestamp for '{filename}': {e}")
                skipped_count += 1
                continue
        else:
            skipped_count += 1
    
    print(f"  Loaded {len(timestamps_dict)} timestamps from {timestamp_file}")
    if skipped_count > 0:
        print(f"  Skipped {skipped_count} rows (did not match prefix '{filename_prefix}')")
    
    # Show sample of loaded timestamps
    if len(timestamps_dict) > 0:
        sorted_nums = sorted(timestamps_dict.keys())
        print(f"  File number range: {sorted_nums[0]} - {sorted_nums[-1]}")
        print(f"  First few files: {sorted_nums[:5]}")
        print(f"  Sample timestamps:")
        for fn in sorted_nums[:3]:
            print(f"    File {fn}: {timestamps_dict[fn]}")
    
    return timestamps_dict


def print_data_summary(data, label="Data"):
    """Print a summary of the extracted data to help verify unique datasets."""
    print(f"\n{label} Summary:")
    print(f"  - Phase angle: {data['ph0']} deg")
    print(f"  - Number of echoes: {len(data['time_echoes'])}")
    print(f"  - First echo time: {data['time_echoes'][0]:.6f} ms")
    print(f"  - Last echo time: {data['time_echoes'][-1]:.6f} ms")
    print(f"  - First 5 peak integrals: {data['peak_int'][:5]}")
    print(f"  - Max integral: {np.max(data['peak_int']):.6f}")
    print(f"  - Mean integral: {np.mean(data['peak_int']):.6f}")


def check_for_duplicates(all_data):
    """Check if datasets appear to be duplicates."""
    for i in range(len(all_data)):
        for j in range(i+1, len(all_data)):
            data1 = all_data[i]
            data2 = all_data[j]
            
            # Check if phase angles are the same
            if abs(data1['ph0'] - data2['ph0']) < 0.1:
                print(f"\n[WARNING] {data1['label']} and {data2['label']} have identical phase angles!")
            
            # Check if first few peak integrals are identical
            if len(data1['peak_int']) == len(data2['peak_int']):
                diff = np.abs(data1['peak_int'] - data2['peak_int'])
                max_diff = np.max(diff)
                if max_diff < 1e-5:
                    print(f"\n[ERROR] {data1['label']} and {data2['label']} appear to be IDENTICAL DATASETS!")
                    print("         This means the same file is being loaded in TNMR.")
                    print("         Please ensure you manually load each different file.")


def generate_file_numbers(start=1, end=188, mode="all", step=None):
    """Return the sequence of file numbers to process.
    
    Parameters:
    -----------
    start : int
        First file number (inclusive)
    end : int
        Last file number (inclusive)
    mode : str
        "all" for all files, "jump4" for every 4th file (default behavior)
    step : int, optional
        Custom step size. If provided, overrides mode-based step calculation.
    """
    if start > end:
        raise ValueError("Start file number must be less than or equal to end file number.")
    if step is None:
        step = 1 if mode == "all" else 4
    return list(range(start, end + 1, step))


def build_processing_plan(file_numbers, base_dir,
                          filename_prefix="CPMG_relaxorption_T2_LiCl_",
                          label_prefix="Sample_"):
    """Construct (filename, directory, label) tuples for downstream processing."""
    return [
        (f"{filename_prefix}{file_num}", base_dir, f"{label_prefix}{file_num}")
        for file_num in file_numbers
    ]


def describe_file_selection(file_numbers, head=5, tail=5):
    """Return a compact string describing the selected file numbers."""
    if not file_numbers:
        return "[]"
    if len(file_numbers) <= head + tail:
        return ", ".join(str(num) for num in file_numbers)
    head_str = ", ".join(str(num) for num in file_numbers[:head])
    tail_str = ", ".join(str(num) for num in file_numbers[-tail:])
    return f"{head_str} ... {tail_str}"


######################## Xigo Data Extraction Function ###########################

def extract_xigo_data(file_path, relaxation_type=1):
    """
    Extract CPMG NMR data from Xigo .nmrdata XML files.
    
    Parameters:
    -----------
    file_path : str
        Full path to the .nmrdata file
    relaxation_type : int
        1 for T1 (Mz signal), 2 for T2 (Mxy signal). Default is 1.
    
    Returns:
    --------
    dict : Dictionary containing extracted data similar to TNMR extraction format
    """
    # Namespace dictionary for the XML file
    namespaces = {'ss': 'urn:schemas-microsoft-com:office:spreadsheet'}
    
    # Check if the file exists
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    print(f"Extracting Xigo data from: {file_path}")
    
    # Read and parse XML file
    with open(file_path, 'r', encoding='utf-8') as f:
        xml_data = f.read()
    
    root = ET.fromstring(xml_data)
    print(f"Parsed XML successfully")
    
    # Initialize lists to hold the data
    data = []
    
    # Extract data from rows using the namespace
    for row in root.findall('.//ss:Row', namespaces):
        cells = row.findall('.//ss:Cell', namespaces)
        row_data = []
        for cell in cells:
            data_element = cell.find('.//ss:Data', namespaces)
            if data_element is not None and data_element.text is not None:
                cell_type = data_element.get('{urn:schemas-microsoft-com:office:spreadsheet}Type')
                if cell_type == 'Number':
                    try:
                        row_data.append(float(data_element.text))
                    except ValueError:
                        row_data.append(data_element.text)
                else:
                    row_data.append(data_element.text)
        if row_data:
            data.append(row_data)
    
    # Convert extracted data to a DataFrame
    df = pd.DataFrame(data)
    print(f"DataFrame shape: {df.shape}")
    
    # Determine search strings based on relaxation type
    if relaxation_type == 1:
        search_str = 'Mz (signal)'
        search_str2 = 'num_experiments'
    elif relaxation_type == 2:
        search_str = 'Mxy'
        search_str2 = 'num_datasets'
    else:
        raise ValueError(f"Invalid relaxation_type: {relaxation_type}. Must be 1 (T1) or 2 (T2)")
    
    # Function to find row and column indices based on search string
    def find_indices(search_str):
        mask = df.map(lambda x: search_str in str(x) if isinstance(x, str) else False)
        row_col_indices = [(index, col) for index, row in mask.iterrows() for col in row[row].index]
        return row_col_indices
    
    # Find indices for time and signal data from dataframe
    row_col_indices = find_indices(search_str)
    if not row_col_indices:
        raise ValueError(f"Could not find '{search_str}' in the data file")
    
    row_index, col_index = row_col_indices[-1]
    print(f"Found data at row {row_index}, column {col_index}")
    
    # Find index for number of datapoints from dataframe
    row_col_indices_num = find_indices(search_str2)
    if not row_col_indices_num:
        raise ValueError(f"Could not find '{search_str2}' in the data file")
    
    num_data = int(df.iloc[row_col_indices_num[0][0], row_col_indices_num[0][1] + 1])
    print(f"Number of data points: {num_data}")
    
    # Extract time and signal values
    t_vals = []
    M_vals = []
    
    for v in range(row_index + 1, row_index + num_data + 1):
        if v < len(df) and col_index - 1 < len(df.columns) and col_index < len(df.columns):
            t_val = df.iloc[v, col_index - 1]
            M_val = df.iloc[v, col_index]
            
            # Convert to float if possible
            try:
                t_val = float(t_val)
                M_val = float(M_val)
                t_vals.append(t_val)
                M_vals.append(M_val)
            except (ValueError, TypeError) as e:
                print(f"Warning: Skipping row {v} due to conversion error: {e}")
                continue
    
    t_clean = np.array(t_vals)
    M_clean = np.array(M_vals)
    
    # Xigo data is already in milliseconds - no conversion needed
    if len(t_clean) > 0:
        max_time = np.max(t_clean)
        min_time = np.min(t_clean)
        print(f"Xigo time data is in milliseconds (min={min_time:.6f} ms, max={max_time:.6f} ms) - no conversion needed")
    
    # Normalize signal (same as TNMR processing)
    M_clean_normalized = M_clean / np.max(M_clean) if np.max(M_clean) > 0 else M_clean
    
    # Calculate signal intensity from raw values (before normalization)
    peak_int_raw = M_clean.copy()
    if len(peak_int_raw) >= 5:
        signal_intensity_raw = np.mean(peak_int_raw[:5])
    else:
        signal_intensity_raw = np.mean(peak_int_raw)
    
    # Create return dictionary compatible with TNMR format
    # Extract filename from path
    filename = os.path.splitext(os.path.basename(file_path))[0]
    fd = os.path.dirname(file_path) + os.sep
    
    # Create dummy exp_params for compatibility (Xigo files may not have all these)
    exp_params = {
        "f1": 0.0,
        "nucleus": "Unknown",
        "SW": 0.0,
        "DW": 0.0,
        "npts": len(t_clean),
        "acq_time": np.max(t_clean) / 1000.0 if len(t_clean) > 0 else 0.0,  # Convert ms to seconds
        "SWfilter": 0.0,
        "rdel": 0.0,
        "nscans": 1,
        "dscans": 0,
        "nreps": len(t_clean),
        "f1amp": 0.0,
        "p90dur": 0.0,
        "p180dur": 0.0,
        "nechoes": len(t_clean),
        "echo_shift": 0.0,
        "echo_time": np.mean(np.diff(t_clean)) if len(t_clean) > 1 else 0.0,  # Average echo spacing in ms
        "echo_pts": 1
    }
    
    return {
        'time_echoes': t_clean,  # Time in milliseconds
        'peak_int': M_clean_normalized,  # Normalized signal
        'peak_int_raw': peak_int_raw,  # Raw (unnormalized) signal
        'signal_intensity_raw': signal_intensity_raw,  # Signal intensity from raw values
        'filename': filename,
        'fd': fd,
        'tau': np.logspace(0, 5, num=512),  # T2 range from 1 ms (10^0) to 100000 ms (10^5)
        'exp_params': exp_params,
        'rfid': None,  # Not available from Xigo
        'ifid': None,  # Not available from Xigo
        'rfid_phased': None,  # Not available from Xigo
        'ifid_phased': None,  # Not available from Xigo
        'time_arr': t_clean,  # Time array
        'start_idxs': np.array([]),  # Not applicable for Xigo
        'end_idxs': np.array([]),  # Not applicable for Xigo
        'ph0': 0.0,  # Not applicable for Xigo
        'center_idxs': np.arange(len(t_clean)),  # Dummy indices
        'actual_peak_positions': np.arange(len(t_clean))  # Dummy positions
    }


######################## Data Truncation Function ###########################

def truncate_dataset(data, start_ms, end_ms):
    """
    Truncate dataset to a specific time range based on time_echoes.
    
    Parameters:
    -----------
    data : dict
        Dataset dictionary containing time_echoes and related arrays
    start_ms : float
        Start time in milliseconds (inclusive)
    end_ms : float
        End time in milliseconds (inclusive)
    
    Returns:
    --------
    data : dict
        Modified dataset dictionary with truncated arrays
    """
    time_echoes = data['time_echoes']
    original_length = len(time_echoes)
    
    # Find indices where time is within the specified range
    mask = (time_echoes >= start_ms) & (time_echoes <= end_ms)
    
    # Truncate time_echoes
    data['time_echoes'] = time_echoes[mask]
    
    # Truncate peak_int and peak_int_raw (must have same length as time_echoes)
    if 'peak_int' in data and len(data['peak_int']) == original_length:
        data['peak_int'] = data['peak_int'][mask]
    if 'peak_int_raw' in data and len(data['peak_int_raw']) == original_length:
        data['peak_int_raw'] = data['peak_int_raw'][mask]
    
    # Truncate FID arrays if present (these may have different lengths)
    # For rfid_phased and ifid_phased, we need to check if they exist and their length
    # Note: These arrays may not align with time_echoes, so we skip them if lengths don't match
    if 'rfid_phased' in data:
        rfid_len = len(data['rfid_phased'])
        if rfid_len == original_length:
            data['rfid_phased'] = data['rfid_phased'][mask]
        # If length doesn't match, we can't reliably truncate, so leave it unchanged
    if 'ifid_phased' in data:
        ifid_len = len(data['ifid_phased'])
        if ifid_len == original_length:
            data['ifid_phased'] = data['ifid_phased'][mask]
    
    # Truncate time_arr if present and has matching length
    if 'time_arr' in data:
        time_arr_len = len(data['time_arr'])
        if time_arr_len == original_length:
            data['time_arr'] = data['time_arr'][mask]
    
    # Update nechoes in exp_params to match new length
    if 'exp_params' in data:
        data['exp_params']['nechoes'] = len(data['time_echoes'])
    
    new_length = len(data['time_echoes'])
    
    return data, original_length, new_length


######################## Main Processing Function ###########################

def main(filename=None, fd="E:/SMS-NMR/Data/test/"):
    """Main function to process CPMG NMR data."""
    
    # User-inputs - directory for saving data
    if fd is None:
        fd = "E:/SMS-NMR/Data/test/"
    
    if filename is None:
        filename = "CPMG_water(tube)_20mMCuSO4(cap)_1"
    
    # ILT analysis parameters
    tau = np.logspace(0, 5, num=512)  # T2 range from 1 ms (10^0) to 100000 ms (10^5)
    
    print("="*60)
    print("EXTRACTING DATA FROM TNMR")
    print("="*60)
    print(f"Extracting data for: {filename}")
    
    # Check if this is a Urea dataset file (2D data with multiple scans)
    # Urea files contain multiple scans and we need to extract only the last scan
    is_urea_dataset = "Urea" in filename or "Urea" in fd or "urea" in filename.lower() or "urea" in fd.lower()
    
    # Connect to TNMR
    NTNMR = win32com.client.Dispatch("NTNMR.Application")
    
    # Construct full file path
    full_path = fd + filename + ".tnt"
    
    # Open file
    try:
        NTNMR.OpenFile(full_path)
        print(f"Opened file: {filename}.tnt")
    except Exception as e:
        print(f"ERROR: Could not open file: {e}")
        raise
    
    # Extract experimental parameters
    # For Urea datasets, use "Acq. Points" instead of "Points 1D" for npts (matches analyze_urea_data.py)
    if is_urea_dataset:
        npts_param_name = "Acq. Points"
    else:
        npts_param_name = "Points 1D"
    
    exp_params = {
        "f1": parse_value(NTNMR.GetNMRParameter("Observe Freq.")),
        "nucleus": NTNMR.GetNMRParameter("Nucleus"),
        "SW": parse_value(NTNMR.GetNMRParameter("SW +/-")),
        "DW": parse_value(NTNMR.GetNMRParameter("Dwell Time")),
        "npts": parse_value(NTNMR.GetNMRParameter(npts_param_name), as_int=True),
        "acq_time": parse_value(NTNMR.GetNMRParameter("Acq. Time")),
        "SWfilter": parse_value(NTNMR.GetNMRParameter("Filter")),
        "rdel": parse_value(NTNMR.GetNMRParameter("Last Delay")),
        "nscans": parse_value(NTNMR.GetNMRParameter("Scans 1D"), as_int=True),
        "dscans": parse_value(NTNMR.GetNMRParameter("Dummy Scans"), as_int=True),
        "nreps": parse_value(NTNMR.GetNMRParameter("Points 2D"), as_int=True),
        "f1amp": parse_value(NTNMR.GetNMRParameter("F1 amp")),
        "p90dur": parse_value(NTNMR.GetNMRParameter("p90")),
        "nechoes": parse_value(NTNMR.GetNMRParameter("Nechoes"), as_int=True),
        "echo_shift": parse_value(NTNMR.GetNMRParameter("Echo_Shift")),
        "echo_time": parse_value(NTNMR.GetNMRParameter("Echo_Time")),
        "echo_pts": parse_value(NTNMR.GetNMRParameter("Acq_pts"), as_int=True)
    }
    
    exp_params["p180dur"] = 2 * exp_params["p90dur"]
    
    print(f"F1: {exp_params['f1']:.6f} MHz")
    print("Nucleus:", exp_params['nucleus'])
    print(f"Sweep Width (SW): {exp_params['SW']:.6f} Hz")
    print(f"Dwell Time (DW): {exp_params['DW']:.3f} us")
    print(f"No. of points (npts): {exp_params['npts']}")
    print(f"Acquisition Time (acq_time): {exp_params['acq_time']:.3f} s")
    print(f"SW Filter: {exp_params['SWfilter']}")
    print(f"Last Delay (rdel): {exp_params['rdel']:.3f} s")
    print(f"Number of Scans (nscans): {exp_params['nscans']}")
    print(f"Dummy Scans (dscans): {exp_params['dscans']}")
    print(f"Repetitions (nreps): {exp_params['nreps']}")
    print(f"F1 Amplitude (f1amp): {exp_params['f1amp']}")
    print(f"90° Pulse Duration (p1): {exp_params['p90dur']:.3f} us")
    print(f"180° Pulse Duration (p2): {exp_params['p180dur']:.3f} us")
    print(f"Number of Echoes (nechoes): {exp_params['nechoes']}")
    print(f"Echo Shift: {exp_params['echo_shift']:.3f} us")
    print(f"Echo Time: {exp_params['echo_time']:.3f} us")
    print(f"Echo Points (echo_pts): {exp_params['echo_pts']}")
    
    print("\n" + "="*60)
    print("EXTRACTING FID")
    print("="*60)
    
    # Use the urea dataset flag determined earlier
    if is_urea_dataset:
        print("="*60)
        print("EXTRACTING FID - LAST SCAN ONLY (Urea Dataset)")
        print("="*60)
        
        # Extract only the last scan (scan #nscans)
        nscans = exp_params["nscans"]
        npts = exp_params["npts"]  # Points per echo
        nechoes = exp_params["nechoes"]  # Number of echoes per scan
        
        # Calculate points per scan: each scan has nechoes echoes, each echo has npts points
        points_per_scan = npts * nechoes
        
        print(f"  Total scans in file: {nscans}")
        print(f"  Points per echo: {npts}")
        print(f"  Echoes per scan: {nechoes}")
        print(f"  Points per scan: {points_per_scan} (npts × nechoes)")
        print(f"  Target: Extract scan #{nscans} (last scan)")
        
        # Try to query TNMR for current scan number (verification)
        current_scan = None
        try:
            scan_query_methods = [
                'GetScan',
                'GetScanNumber',
                'CurrentScan',
                'ScanNumber',
                'GetCurrentScan',
            ]
            for method_name in scan_query_methods:
                try:
                    if hasattr(NTNMR, method_name):
                        current_scan = getattr(NTNMR, method_name)()
                        if isinstance(current_scan, (int, float)):
                            print(f"  [INFO] TNMR reports current scan: #{int(current_scan)}")
                            break
                except:
                    continue
        except:
            pass
        
        # Try to programmatically select scan #nscans before extraction
        if current_scan is None or current_scan != nscans:
            print(f"  [INFO] Attempting to select scan #{nscans} before extraction...")
            scan_selected = False
            try:
                scan_selection_methods = [
                    ('SetScan', nscans),
                    ('SelectScan', nscans),
                    ('GotoScan', nscans),
                    ('SetScanNumber', nscans),
                    ('Scan', nscans),
                ]
                
                for method_name, scan_num in scan_selection_methods:
                    try:
                        if hasattr(NTNMR, method_name):
                            getattr(NTNMR, method_name)(scan_num)
                            print(f"  [OK] Selected scan #{scan_num} using {method_name}()")
                            scan_selected = True
                            time.sleep(0.5)  # Wait for scan to be selected (reduced from 1s to avoid delays)
                            break
                    except Exception as e:
                        print(f"  [DEBUG] Method {method_name}() failed: {e}")
                        continue
                
                if not scan_selected:
                    print(f"  [INFO] Could not programmatically select scan #{nscans} (TNMR methods not available)")
                    print(f"  [INFO] Will extract from data array position instead (should still get scan #{nscans})")
            except Exception as e:
                print(f"  [INFO] Scan selection attempt failed, will extract from data array position")
        else:
            print(f"  [OK] TNMR already reports scan #{current_scan} is selected (matches target)")
        
        # Extract FID from CPMG experiment loaded on TNMR
        # Note: TNMR.GetData is a property (not a method) - returns all scans concatenated or just the selected scan
        print(f"  [INFO] Accessing NTNMR.GetData property to extract FID data...")
        try:
            raw_data = NTNMR.GetData  # GetData is a property, not a method - no parentheses!
            print(f"  [INFO] GetData property accessed successfully, converting to numpy array...")
        except Exception as e:
            print(f"  [ERROR] NTNMR.GetData access failed: {e}")
            print(f"  [ERROR] This may indicate TNMR is not responding or the file is locked.")
            print(f"  [ERROR] Please ensure:")
            print(f"    1. TNMR is running and the file is loaded")
            print(f"    2. The file is not open in another program")
            print(f"    3. TNMR is not waiting for user input")
            raise
        arr = np.array(raw_data, dtype=float)
        arr = arr.reshape(-1, 2)
        
        total_points = len(arr)
        print(f"  Total data points extracted: {total_points}")
        
        # Always extract the last scan from the data array
        # Strategy: Check if we have multiple scans, and if so, extract the last one
        expected_total_points = points_per_scan * nscans
        
        # Track scan_start_idx for verification
        scan_start_idx = None
        
        if total_points >= expected_total_points:
            # We have all scans concatenated - extract last scan
            # Verify the data structure matches expectations
            if total_points == expected_total_points:
                print(f"  [OK] Data structure verified: {total_points} points = {nscans} scans × {points_per_scan} points/scan")
            else:
                print(f"  [INFO] Data has {total_points} points, expected {expected_total_points} points")
                print(f"  [INFO] Extracting last scan assuming sequential storage")
            
            # Calculate indices for scan #nscans (last scan)
            scan_start_idx = (nscans - 1) * points_per_scan
            scan_end_idx = nscans * points_per_scan
            
            # Verify we're extracting from the end of the data
            if scan_end_idx > total_points:
                print(f"  [WARNING] Calculated end index ({scan_end_idx}) exceeds total points ({total_points})")
                print(f"  [WARNING] Adjusting to extract from end of data")
                scan_end_idx = total_points
                scan_start_idx = total_points - points_per_scan
            
            # Extract the last scan using calculated indices
            arr_last_scan_calculated = arr[scan_start_idx:scan_end_idx]
            
            # Also extract directly from the end as verification
            arr_last_scan_direct = arr[-points_per_scan:]
            
            # Verify both methods give the same result (ensures we're getting the last scan)
            if np.array_equal(arr_last_scan_calculated, arr_last_scan_direct):
                arr_last_scan = arr_last_scan_calculated
                print(f"  [OK] Extracted scan #{nscans} from concatenated data (all {nscans} scans)")
                print(f"       Scan #{nscans} indices: {scan_start_idx} to {scan_end_idx}")
                print(f"       Extracted {len(arr_last_scan)} points ({nechoes} echoes × {npts} points/echo)")
                print(f"       [VERIFIED] Calculated extraction matches direct end extraction - confirmed last scan")
                
                # Additional verification: Check that we're extracting from the correct position
                # Scan #nscans should be at indices (nscans-1)*points_per_scan to nscans*points_per_scan
                expected_start = (nscans - 1) * points_per_scan
                if scan_start_idx == expected_start:
                    print(f"       [VERIFIED] Start index {scan_start_idx} matches expected position for scan #{nscans}")
                else:
                    print(f"       [WARNING] Start index {scan_start_idx} differs from expected {expected_start} for scan #{nscans}")
            else:
                # If they don't match, use the direct extraction from end (most reliable)
                print(f"  [WARNING] Calculated extraction differs from direct end extraction")
                print(f"  [WARNING] Using direct extraction from end of data (most reliable)")
                scan_start_idx = total_points - points_per_scan  # Update for verification
                arr_last_scan = arr_last_scan_direct
                print(f"  [OK] Extracted last {len(arr_last_scan)} points directly from end of data")
                print(f"       This ensures we get the actual last scan regardless of scan numbering")
            
            # Final verification
            if len(arr_last_scan) == points_per_scan:
                print(f"  [VERIFIED] Extracted data matches expected scan size ({points_per_scan} points)")
            else:
                print(f"  [WARNING] Extracted {len(arr_last_scan)} points, expected {points_per_scan} points")
                print(f"  [WARNING] This may indicate incorrect scan extraction")
        elif total_points > points_per_scan:
            # We have multiple scans but not exactly points_per_scan * nscans
            # Extract directly from the end to ensure we get the last scan
            estimated_nscans = total_points // points_per_scan
            scan_start_idx = total_points - points_per_scan  # Track position for verification
            arr_last_scan = arr[-points_per_scan:]  # Always extract from end
            
            if estimated_nscans > 0:
                print(f"  [OK] Extracted last scan from data (estimated {estimated_nscans} scans)")
                print(f"       Extracted last {points_per_scan} points directly from end of data")
                print(f"       Extracted {len(arr_last_scan)} points ({nechoes} echoes × {npts} points/echo)")
                print(f"       [VERIFIED] Direct extraction ensures we get the actual last scan")
            else:
                print(f"  [OK] Extracted last {points_per_scan} points directly from end as scan #{nscans}")
                print(f"       [VERIFIED] Direct extraction ensures we get the actual last scan")
        elif total_points == points_per_scan:
            # We have exactly one scan - TNMR might only return the selected scan
            # Try to programmatically select scan #nscans and re-extract
            print(f"  [INFO] Got single scan ({points_per_scan} points)")
            print(f"  [INFO] Attempting to select scan #{nscans} programmatically...")
            
            scan_selected = False
            try:
                scan_selection_methods = [
                    ('SetScan', nscans),
                    ('SelectScan', nscans),
                    ('GotoScan', nscans),
                    ('SetScanNumber', nscans),
                    ('Scan', nscans),
                ]
                
                for method_name, scan_num in scan_selection_methods:
                    try:
                        if hasattr(NTNMR, method_name):
                            getattr(NTNMR, method_name)(scan_num)
                            print(f"  [OK] Selected scan #{scan_num} using {method_name}()")
                            scan_selected = True
                            time.sleep(0.5)  # Wait for scan to be selected (reduced from 1s to avoid delays)
                            break
                    except Exception as e:
                        print(f"  [DEBUG] Method {method_name}() failed: {e}")
                        continue
            except Exception as e:
                print(f"  [DEBUG] Scan selection block failed: {e}")
                pass
            
            if scan_selected:
                # Re-extract data after selecting scan #nscans
                print(f"  [INFO] Re-extracting data after selecting scan #{nscans}...")
                raw_data = NTNMR.GetData  # GetData is a property, not a method - no parentheses!
                arr = np.array(raw_data, dtype=float)
                arr = arr.reshape(-1, 2)
                total_points = len(arr)
                print(f"  [INFO] Re-extracted {total_points} points")
            
            if total_points == points_per_scan:
                # Still only one scan - use it (should be scan #nscans if selection worked)
                arr_last_scan = arr
                scan_start_idx = 0  # Single scan starts at beginning
                print(f"  [OK] Using single scan ({points_per_scan} points)")
                print(f"  [INFO] Assuming this is scan #{nscans} (verify in TNMR if needed)")
            else:
                # Got multiple scans after selection - extract last one
                if total_points >= points_per_scan * nscans:
                    scan_start_idx = (nscans - 1) * points_per_scan
                    scan_end_idx = nscans * points_per_scan
                    arr_last_scan = arr[scan_start_idx:scan_end_idx]
                    print(f"  [OK] Extracted scan #{nscans} after selection")
                else:
                    # Extract last points_per_scan points
                    scan_start_idx = total_points - points_per_scan
                    arr_last_scan = arr[-points_per_scan:]
                    print(f"  [OK] Extracted last {points_per_scan} points as scan #{nscans}")
        else:
            # Less than one scan worth of data - extract what we can
            print(f"  [WARNING] Unexpected data structure")
            print(f"           Total points: {total_points}, expected at least {points_per_scan}")
            print(f"           Attempting to extract last {min(points_per_scan, total_points)} points...")
            scan_start_idx = max(0, total_points - points_per_scan)
            arr_last_scan = arr[-min(points_per_scan, total_points):]
        
        # Ensure we have exactly points_per_scan points (pad with zeros if needed, truncate if too many)
        if len(arr_last_scan) < points_per_scan:
            print(f"  [WARNING] Extracted scan has {len(arr_last_scan)} points, expected {points_per_scan}")
            print(f"  [WARNING] Padding with zeros to {points_per_scan} points")
            padding = np.zeros((points_per_scan - len(arr_last_scan), 2))
            arr_last_scan = np.vstack([arr_last_scan, padding])
        elif len(arr_last_scan) > points_per_scan:
            print(f"  [WARNING] Extracted scan has {len(arr_last_scan)} points, expected {points_per_scan}")
            print(f"  [WARNING] Truncating to {points_per_scan} points")
            arr_last_scan = arr_last_scan[:points_per_scan]
        
        fid = arr_last_scan[:, 0] + 1j * arr_last_scan[:, 1]
        rfid = np.real(fid)
        ifid = np.imag(fid)
        
        # Final verification: Try to confirm which scan we extracted
        final_scan_check = None
        try:
            for method_name in ['GetScan', 'GetScanNumber', 'CurrentScan', 'ScanNumber', 'GetCurrentScan']:
                try:
                    if hasattr(NTNMR, method_name):
                        final_scan_check = getattr(NTNMR, method_name)()
                        if isinstance(final_scan_check, (int, float)):
                            break
                except:
                    continue
        except:
            pass
        
        print(f"  [OK] Final FID length: {len(fid)} points")
        
        # Verify which scan was extracted using multiple methods
        verification_passed = False
        
        # Method 1: Check TNMR's reported scan number
        if final_scan_check is not None:
            print(f"  [VERIFIED] TNMR reports scan #{int(final_scan_check)} is currently selected")
            if int(final_scan_check) == nscans:
                print(f"  [VERIFIED] Successfully extracted scan #{nscans} (last scan)")
                verification_passed = True
            else:
                print(f"  [WARNING] TNMR reports scan #{int(final_scan_check)}, but we targeted scan #{nscans}")
                print(f"  [WARNING] Extracted data may be from scan #{int(final_scan_check)} instead")
        
        # Method 2: Verify by data position if we have all scans
        if not verification_passed and scan_start_idx is not None:
            scan_number_from_position = (scan_start_idx // points_per_scan) + 1
            print(f"  [VERIFIED] Extracted scan #{scan_number_from_position} based on data position (index {scan_start_idx})")
            if scan_number_from_position == nscans:
                print(f"  [VERIFIED] Successfully extracted scan #{nscans} (last scan) from position in data array")
                verification_passed = True
            else:
                print(f"  [WARNING] Position indicates scan #{scan_number_from_position}, not scan #{nscans}")
        elif not verification_passed and total_points >= expected_total_points:
            # Calculate from end position if scan_start_idx not available
            scan_number_from_position = (total_points // points_per_scan)
            print(f"  [VERIFIED] Extracted scan #{scan_number_from_position} based on data array size")
            if scan_number_from_position == nscans:
                print(f"  [VERIFIED] Successfully extracted scan #{nscans} (last scan) from end of data array")
                verification_passed = True
        
        if not verification_passed:
            print(f"  [INFO] Extracted {len(fid)} points (targeted scan #{nscans} - verify in TNMR if needed)")
            print(f"  [INFO] To verify: Check TNMR interface to confirm which scan is currently displayed")
        
        # Store scan number for later use
        extracted_scan_number = nscans
        
    else:
        # Standard extraction for non-Urea datasets (all data)
        # Using direct method from nmr_dvs_correlation.py
        print("="*60)
        print("EXTRACTING FID - ALL DATA")
        print("="*60)
        
        # Get FID data (direct method from nmr_dvs_correlation.py)
        npts = exp_params["npts"]
        print(f"  [INFO] Accessing NTNMR.GetData property to extract FID data...")
        try:
            raw_data = NTNMR.GetData  # GetData is a property, not a method - no parentheses!
            print(f"  [INFO] GetData property accessed successfully, converting to numpy array...")
        except Exception as e:
            print(f"  [ERROR] NTNMR.GetData access failed: {e}")
            print(f"  [ERROR] This may indicate TNMR is not responding or the file is locked.")
            print(f"  [ERROR] Please ensure:")
            print(f"    1. TNMR is running and the file is loaded")
            print(f"    2. The file is not open in another program")
            print(f"    3. TNMR is not waiting for user input")
            raise
        
        # Extract FID (direct method)
        arr = np.array(raw_data[:npts * 2], dtype=float).reshape(npts, 2)
        fid = arr[:, 0] + 1j * arr[:, 1]
        rfid = np.real(fid)
        ifid = np.imag(fid)
        
        extracted_scan_number = None  # Not applicable for non-Urea datasets
    
    print("\n" + "="*60)
    print("AUTO-PHASING FID")
    print("="*60)
    
    # Auto-phase FID using peak of real echo
    phases = np.arange(-180, 180)
    max_int = []
    
    for n in phases:
        fid_phased = fid * np.exp(-1j * n * np.pi / 180)
        rfid_phased = np.real(fid_phased)
        max_int.append(np.max(rfid_phased))
    
    peak_max = np.array(max_int)
    
    max_idx = np.argmax(peak_max)
    ph0 = phases[max_idx]
    print(f'Autophase angle: {ph0} deg')
    
    fid_phased = fid * np.exp(-1j * ph0 * np.pi / 180)
    rfid_phased = np.real(fid_phased)
    ifid_phased = np.imag(fid_phased)
    
    print("\n" + "="*60)
    print("INTEGRATING ECHOES")
    print("="*60)
    
    # CRITICAL FIX: Use echo_pts for spacing - echoes are stored back-to-back in FID
    # echo_time is the physical time between echoes, but echo_pts is the spacing in the FID array
    
    print(f"\nEcho integration strategy:")
    print(f"  Using echo_pts for spacing (echoes stored back-to-back in FID)")
    
    # The FID contains echoes stored sequentially, so spacing is echo_pts
    # echo_time is the physical time between echoes, but only echo_pts points are stored per echo
    echo_pts = exp_params["echo_pts"]  # Points per echo in the FID
    echo_time_us = exp_params["echo_time"]  # Physical time between echoes (for time calculation)
    dwell_time_us = exp_params["DW"]  # microseconds per point
    
    # Spacing in FID array is echo_pts (echoes are back-to-back)
    points_per_echo = echo_pts
    
    # Convert to seconds for time calculation
    echo_spacing_seconds = echo_time_us * 1e-6
    
    print(f"  Echo points (echo_pts): {echo_pts} points per echo in FID")
    print(f"  Echo time parameter: {echo_time_us} μs (physical time between echoes)")
    print(f"  Dwell time: {dwell_time_us} μs per point")
    print(f"  Spacing in FID array: {points_per_echo} points per echo (echoes are back-to-back)")
    print(f"  Echo spacing in time: {echo_spacing_seconds:.6f} seconds ({echo_spacing_seconds*1000:.3f} ms)")
    
    # For Urea datasets, use simple echo integration method (matches analyze_urea_data.py)
    # For other datasets, use peak detection method
    if is_urea_dataset:
        # Simple echo integration method - matches notebook exactly (from analyze_urea_data.py)
        # No peak detection needed - just calculate echo positions from start
        actual_npts = len(rfid_phased)
        
        # Calculate first echo position: int(echo_pts/2) - matches notebook
        first_peak_idx = int(points_per_echo / 2)
        
        # Calculate how many echoes we can fit
        max_possible_echoes = (actual_npts - first_peak_idx) // points_per_echo
        actual_nechoes = min(exp_params["nechoes"], max_possible_echoes)
        
        print(f"  Using simple echo integration method (matching analyze_urea_data.py):")
        print(f"     First echo center: index {first_peak_idx} (int(echo_pts/2))")
        print(f"     Echo spacing: {points_per_echo} points")
        print(f"     Expected echoes: {exp_params['nechoes']}, fitting: {actual_nechoes}")
        
        # Generate echo centers at exact spacing
        center_idxs = [first_peak_idx + n * points_per_echo for n in range(actual_nechoes)]
        center_idxs = np.array(center_idxs)
        center_idxs = center_idxs[center_idxs < actual_npts]  # Remove any that exceed array bounds
        actual_nechoes = len(center_idxs)
        
        print(f"  Generated {actual_nechoes} echo positions")
        if actual_nechoes > 0:
            print(f"     First echo at index: {center_idxs[0]}")
            print(f"     Last echo at index: {center_idxs[-1]}")
        
        if actual_nechoes == 0:
            raise ValueError(f"No echoes can be fitted. FID has {actual_npts} points, need at least {points_per_echo} points for one echo.")
    else:
        # CRITICAL FIX: Find FIRST echo, then generate ALL echoes at EXACT spacing
        # This ensures we get all echoes, not just detected peaks
        signal_abs = np.abs(rfid_phased)
        
        print(f"  Finding first echo, then generating all echoes at exact {points_per_echo}-point spacing...")
        
        # Find the first echo by searching in the initial region
        # The first echo should be within the first few echo periods
        search_window = min(points_per_echo * 10, len(signal_abs) // 5)  # Search first 10 echo periods or 20% of FID
        search_region = signal_abs[:search_window]
        
        # Find multiple peaks in the search region to identify the first real echo
        # Use peak detection to find the first significant peak
        # Find peaks in the search region
        # Minimum height should be at least 10% of the maximum in this region
        min_height = np.max(search_region) * 0.1
        peaks_in_region, properties = find_peaks(search_region, height=min_height, distance=points_per_echo // 2)
        
        if len(peaks_in_region) > 0:
            # Use the first detected peak as the first echo
            first_echo_idx = peaks_in_region[0]
            print(f"  First echo detected at index: {first_echo_idx} (using peak detection)")
            
            # Verify this is likely the first echo by checking if there's a peak at expected spacing
            verification_window = points_per_echo // 3  # 33% tolerance
            check_idx = first_echo_idx + points_per_echo
            if check_idx < len(signal_abs):
                check_start = max(check_idx - verification_window, 0)
                check_end = min(check_idx + verification_window, len(signal_abs))
                check_region = signal_abs[check_start:check_end]
                if len(check_region) > 0 and np.max(check_region) > np.max(search_region) * 0.3:
                    second_peak_idx = check_start + np.argmax(check_region)
                    print(f"  First echo verified: second echo found at index {second_peak_idx} (expected ~{check_idx})")
                    print(f"  Spacing between first two echoes: {second_peak_idx - first_echo_idx} points (expected {points_per_echo})")
                else:
                    print(f"  First echo at index: {first_echo_idx} (verification inconclusive)")
            else:
                print(f"  First echo at index: {first_echo_idx}")
        else:
            # Fallback: use maximum in search region
            first_echo_idx = np.argmax(search_region)
            print(f"  [WARNING] No peaks detected in search region, using maximum at index: {first_echo_idx}")
        
        # Now generate ALL echo positions at EXACT spacing from the first echo
        actual_npts = len(rfid_phased)
        max_possible_echoes = (actual_npts - first_echo_idx) // points_per_echo
        actual_nechoes = min(exp_params["nechoes"], max_possible_echoes)
        
        # Generate all echo center positions at exact spacing
        center_idxs = [first_echo_idx + n * points_per_echo for n in range(actual_nechoes)]
        center_idxs = np.array(center_idxs)
        
        # Verify all positions are within FID bounds (for non-urea path)
        center_idxs = center_idxs[center_idxs < actual_npts]
        actual_nechoes = len(center_idxs)
    
    # For urea path, center_idxs is already filtered above
    # For non-urea path, center_idxs is filtered in the else block above
    # Both paths now have center_idxs and actual_nechoes defined
    
    # Print summary (only if we have echoes)
    if actual_nechoes > 0:
        print(f"  Generated {actual_nechoes} echo positions at exact {points_per_echo}-point spacing")
        print(f"  First echo at index: {center_idxs[0]}")
        print(f"  Last echo at index: {center_idxs[-1]}")
        print(f"  Requested echoes: {exp_params['nechoes']}")
    else:
        print(f"  [ERROR] No echoes could be generated!")
        print(f"  Requested echoes: {exp_params['nechoes']}")
    
    # Verify spacing is exactly correct
    if len(center_idxs) > 1:
        spacing_check = np.diff(center_idxs)
        if np.all(spacing_check == points_per_echo):
            print(f"  [OK] All {actual_nechoes} echoes are consecutive with uniform {points_per_echo}-point spacing")
        else:
            # This should never happen, but check anyway
            unique_spacings = np.unique(spacing_check)
            print(f"  [WARNING] Spacing not uniform! Unique spacing values: {unique_spacings}")
    
    print(f"\n  === DEBUGGING ECHO POSITIONS ===")
    print(f"  First echo at index: {center_idxs[0]}")
    print(f"  Calculated spacing: {points_per_echo} points per echo")
    print(f"  First 10 echo positions: {center_idxs[:10]}")
    
    # Calculate time differences
    # Note: Array spacing is echo_pts (16 points), but physical time spacing is echo_time (200 μs)
    dwell_time_s_debug = exp_params["DW"] * 1e-6
    array_time_spacing = points_per_echo * dwell_time_s_debug  # Time for array spacing (16 points × 2 μs = 32 μs)
    print(f"  Array spacing: {points_per_echo} points = {array_time_spacing*1e6:.1f} μs")
    print(f"  Physical echo spacing: {echo_time_us} μs = {echo_spacing_seconds*1e6:.1f} μs")
    print(f"  Note: Echoes are stored back-to-back in FID, but physically spaced by echo_time")
    
    print(f"  Last echo at index: {center_idxs[-1]}")
    
    # Verify spacing is correct
    if len(center_idxs) > 1:
        spacing_check = np.diff(center_idxs)
        if np.all(spacing_check == points_per_echo):
            print(f"  [OK] All echoes are consecutive with uniform spacing")
        else:
            print(f"  [ERROR] Spacing verification failed!")
            print(f"  First 10 spacing values: {spacing_check[:10]}")
            print(f"  Expected: {points_per_echo}")
    
    # Create time array based on actual FID length
    # Each point is separated by DW (dwell time)
    actual_npts = len(rfid_phased)
    dwell_time_s = exp_params["DW"] * 1e-6  # Convert μs to seconds
    
    if is_urea_dataset:
        # For Urea datasets: time spans from 0 to scan_acq_time (only the extracted scan)
        scan_acq_time = actual_npts * exp_params["DW"] * 1e-6  # Total time for this scan in seconds
        time_arr = np.linspace(0, scan_acq_time, actual_npts)  # Matches notebook: np.linspace(0, acq_time, npts)
        print(f"  FID length: {actual_npts} points (extracted scan #{extracted_scan_number})")
        print(f"  Time array: spans from 0 to {scan_acq_time:.6f} seconds (scan acquisition time)")
        print(f"  Time array: each point separated by {dwell_time_s:.6f} seconds ({exp_params['DW']} μs)")
    else:
        # Standard time array for non-Urea datasets
        time_arr = np.arange(actual_npts) * dwell_time_s  # Correct: each point = index * DW
        print(f"  FID length: {actual_npts} points")
        print(f"  Time array: each point separated by {dwell_time_s:.6f} seconds ({exp_params['DW']} μs)")
    
    # Integration - refined window method: find local minima within fixed window
    # Ensure contiguity by using previous peak's right_min as current peak's left_min
    peak_int = []
    start_idx = []
    end_idx = []
    actual_peak_positions = []
    
    print(f"  Integration window: refined by finding local minima within fixed window")
    print(f"     Fixed window size: center ± (echo_pts//2 + 1) points")
    
    # Store right_min from previous peak to ensure contiguity
    prev_right_min = None
    
    for n in range(len(center_idxs)):
        center = center_idxs[n]
        
        # Step 1: Define fixed window boundaries (as before)
        fixed_window_start = max(center - (points_per_echo // 2) - 1, 0)
        fixed_window_end = min(center + (points_per_echo // 2) + 1, len(rfid_phased))
        
        # Step 2: Find local minimum to the left of current center
        # If we have previous peak's right_min, use it directly to ensure contiguity
        if prev_right_min is not None:
            # Use previous peak's right_min as this peak's left_min (guarantees contiguity)
            left_min_idx = prev_right_min
        else:
            # First peak: search from fixed_window_start to center
            left_search_start = fixed_window_start
            left_search_end = center
            
            if left_search_end > left_search_start:
                left_region = np.abs(rfid_phased[left_search_start:left_search_end])
                if len(left_region) > 0:
                    left_min_idx_local = np.argmin(left_region)
                    left_min_idx = left_search_start + left_min_idx_local
                else:
                    left_min_idx = left_search_start
            else:
                left_min_idx = left_search_start
        
        # Step 3: Find right boundary (minimum between current and next peak)
        if n < len(center_idxs) - 1:
            # There is a next peak - find the minimum between current and next peak
            next_center = center_idxs[n + 1]
            # Search region: from current center to next center
            search_start = center
            search_end = next_center
            
            if search_end > search_start:
                search_region = np.abs(rfid_phased[search_start:search_end])
                if len(search_region) > 0:
                    # Find the minimum in the region between current and next peak
                    min_idx_local = np.argmin(search_region)
                    right_min_idx = search_start + min_idx_local
                else:
                    right_min_idx = fixed_window_end
            else:
                right_min_idx = fixed_window_end
        else:
            # Last echo: fallback to finding right minimum within its own fixed window
            right_search_start = center
            right_search_end = fixed_window_end
            if right_search_end > right_search_start:
                right_region = np.abs(rfid_phased[right_search_start:right_search_end])
                if len(right_region) > 0:
                    right_min_idx_local = np.argmin(right_region)
                    right_min_idx = right_search_start + right_min_idx_local
                else:
                    right_min_idx = fixed_window_end
            else:
                right_min_idx = fixed_window_end
        
        # Store right_min for next iteration to ensure contiguity
        prev_right_min = right_min_idx
        
        # Step 4: Use refined window boundaries
        # Window starts at left minimum, ends at right minimum (which is next peak's left_min)
        window_start = left_min_idx
        window_end = right_min_idx
        
        # Ensure window doesn't go beyond array bounds
        window_start = max(window_start, 0)
        window_end = min(window_end, len(rfid_phased))
        
        # Ensure minimum window size (at least 3 points)
        # But don't expand window_end if it would break contiguity with next peak
        min_window_size = 3
        if window_end - window_start < min_window_size:
            # Only expand window_start if needed (don't expand window_end to maintain contiguity)
            needed_expansion = min_window_size - (window_end - window_start)
            window_start = max(window_start - needed_expansion, 0)
            # window_end stays the same to maintain contiguity
        
        start_idx.append(window_start)
        end_idx.append(window_end)
        actual_peak_positions.append(center)
        
        # Integrate using trapezoidal rule over refined window
        integral = np.trapz(rfid_phased[window_start:window_end], time_arr[window_start:window_end])
        peak_int.append(integral)
        
        # Debug output for first 3 and last 3 echoes
        if n < 3 or n >= len(center_idxs) - 3:
            left_min_source = "from prev peak" if n > 0 else "calculated"
            next_echo_info = ""
            if n < len(center_idxs) - 1:
                next_echo_info = f" (will be next peak's left_min)"
            print(f"    Echo {n+1}: center={center}, left_min={left_min_idx} ({left_min_source}), "
                  f"right_min={right_min_idx}{next_echo_info}, refined=[{window_start}, {window_end}], "
                  f"width={window_end-window_start} points")
    
    # Verify windows are contiguous (for debugging)
    if len(start_idx) > 1:
        gaps_found = []
        for i in range(len(start_idx) - 1):
            if end_idx[i] != start_idx[i + 1]:
                gaps_found.append((i+1, end_idx[i], start_idx[i+1], start_idx[i+1] - end_idx[i]))
        if gaps_found:
            print(f"  [WARNING] Found {len(gaps_found)} gaps between integration windows:")
            for gap_info in gaps_found[:5]:  # Show first 5 gaps
                print(f"    Between echo {gap_info[0]} and {gap_info[0]+1}: end={gap_info[1]}, start={gap_info[2]}, gap={gap_info[3]} points")
        else:
            print(f"  [OK] All {len(start_idx)} integration windows are contiguous (no gaps)")
    
    peak_int = np.array(peak_int)
    peak_int_raw = peak_int.copy()  # Keep for backwards compatibility, but same as peak_int now
    
    # Calculate signal intensity from RAW (unnormalized) peak integrals
    if len(peak_int_raw) >= 5:
        signal_intensity_raw = np.mean(peak_int_raw[:5])
    else:
        # If fewer than 5 peaks available, use all available peaks
        signal_intensity_raw = np.mean(peak_int_raw)
    
    # No normalization - using raw peak integrals directly
    start_idxs = np.array(start_idx)
    end_idxs = np.array(end_idx)
    center_idxs = np.array(center_idxs)  # Convert back to numpy array
    actual_peak_positions = np.array(actual_peak_positions)  # Actual peak positions within integration windows
    
    # Get echo times - use physical echo_time for spacing, not array spacing
    # The first echo time is based on its position in the array
    # But subsequent echoes are physically spaced by echo_time (200 μs), not by array spacing
    first_echo_time_s = time_arr[center_idxs[0]]  # Time of first echo from array
    time_echoes = np.array([first_echo_time_s + n * echo_spacing_seconds for n in range(len(center_idxs))]) * 1000  # Convert to milliseconds
    
    print(f"Integrated {len(peak_int)} echoes")
    print(f"First echo at index: {center_idxs[0]}")
    print(f"Last echo at index: {center_idxs[-1]}")
    
    # Print unique identifiers to verify correct file loaded
    print(f"\n*** VERIFICATION FOR {filename} ***")
    if is_urea_dataset:
        print(f"Analyzed scan: #{extracted_scan_number} (last scan only)")
    print(f"Phase angle: {ph0} deg")
    print(f"Number of echoes: {len(peak_int)}")
    print(f"First 3 peak integrals (normalized): {peak_int[:3]}")
    print(f"First 3 peak integrals (raw): {peak_int_raw[:3]}")
    print(f"Max peak integral (raw): {np.max(peak_int_raw):.6f}")
    print(f"Signal intensity (raw, avg of first 5): {signal_intensity_raw:.6f}")
    print("*" * 60)
    
    # Close file (direct method from nmr_dvs_correlation.py)
    try:
        NTNMR.CloseActiveFile
    except:
        pass
    
    return {
        'time_echoes': time_echoes,
        'peak_int': peak_int,  # Same as peak_int_raw (no normalization) - kept for compatibility
        'peak_int_raw': peak_int_raw,  # Raw (unnormalized) values - used for ILT analysis
        'signal_intensity_raw': signal_intensity_raw,  # Signal intensity from raw values
        'filename': filename,
        'fd': fd,
        'tau': tau,
        'exp_params': exp_params,
        'rfid': rfid,
        'ifid': ifid,
        'rfid_phased': rfid_phased,
        'ifid_phased': ifid_phased,
        'time_arr': time_arr,
        'start_idxs': start_idxs,
        'end_idxs': end_idxs,
        'ph0': ph0,
        'center_idxs': center_idxs,
        'actual_peak_positions': actual_peak_positions,
        'scan_number': extracted_scan_number if is_urea_dataset else None  # Store which scan was analyzed (for Urea datasets)
    }


def parse_cli_args():
    """Parse command line arguments for batch processing."""
    parser = argparse.ArgumentParser(
        description="CPMG NMR data processing with ILT analysis."
    )
    parser.add_argument(
        "--mode",
        choices=["all", "jump4"],
        default="jump4",
        help="Select 'all' files or every 4th file via 'jump4' mode (default)."
    )
    parser.add_argument(
        "--start",
        type=int,
        default=1,
        help="First file number to include (inclusive)."
    )
    parser.add_argument(
        "--end",
        type=int,
        default=188,
        help="Last file number to include (inclusive)."
    )
    parser.add_argument(
        "--base-dir",
        type=str,
        default=None,
        help="Base directory for data files (e.g., 'E:/SMS-NMR/Data/LiCl/LiCl/' or 'E:/SMS-NMR/Data/Mg(NO3)2/')."
    )
    parser.add_argument(
        "--filename-prefix",
        type=str,
        default=None,
        help="Filename prefix (e.g., 'CPMG_relaxorption_T2_LiCl_' or 'CPMG_relaxorption_T2_Mg(NO3)2_')."
    )
    parser.add_argument(
        "--reference-file",
        type=int,
        default=None,
        help="File number to use as reference for global lambda optimization (e.g., 152 or 100)."
    )
    parser.add_argument(
        "--truncate",
        type=str,
        default=None,
        help="Truncate data to time range (e.g., '0-450' for 0 to 450ms)."
    )
    return parser.parse_args()


if __name__ == "__main__":
    # Parse CLI arguments first (needed for reference_file even if data_source is Xigo)
    args = parse_cli_args()
    
    # Define available datasets
    # To add a new dataset, add an entry to this dictionary with:
    #   - 'name': Display name for the dataset
    #   - 'base_dir': Base directory path (with trailing slash)
    #   - 'filename_prefix': Prefix pattern for filenames
    #   - 'reference_file': File number to use for lambda optimization
    #   - 'default_start': Default starting file number
    #   - 'default_end': Default ending file number
    datasets = {
        '1': {
            'name': 'LiCl Dataset',
            'base_dir': 'E:/SMS-NMR/Data/LiCl/LiCl/',
            'filename_prefix': 'CPMG_relaxorption_T2_LiCl_',
            'reference_file': 152,
            'default_start': 40,
            'default_end': 188
        },
        '2': {
            'name': 'Mg(NO3)2 Dataset',
            'base_dir': 'E:/SMS-NMR/Data/Mg(NO3)2/',
            'filename_prefix': 'CPMG_relaxorption_T2_Mg(NO3)2_',
            'reference_file': 100,
            'default_start': 40,
            'default_end': 153
        },
        '3': {
            'name': 'Lewatit Water Dataset',
            'base_dir': 'E:/SMS-NMR/Data/20251120_Lewatit_water/',
            'filename_prefix': 'CPMG_relaxorption_T2_lewatit_',
            'reference_file': 90,
            'default_start': 1,
            'default_end': 92
        },
        '4': {
            'name': 'Urea Dataset',
            'base_dir': 'E:/SMS-NMR/Data/Urea/',
            'filename_prefix': 'CPMG_Urea_20250904_',
            'reference_file': 6,
            'default_start': 1,
            'default_end': 11
        },
        '5': {
            'name': 'LiCl Dataset (0.8T)',
            'base_dir': 'E:/SMS-NMR/Data/LiCl (0.8T)/20251121_LiCl_water/',
            'filename_prefix': 'CPMG_relaxorption_T2_LiCl_',
            'reference_file': 55,
            'default_start': 1,
            'default_end': 110
        },
        '6': {
        'name': 'Avicel Water 1',
        'base_dir': 'E:/SMS-NMR/Data/Avicel/20251117_avicel_water_1/',
        'filename_prefix': 'CPMG_relaxorption_T2_avicel_',
        'reference_file': 90,
        'default_start': 1,
        'default_end': 129
        },
        '7': {
        'name': 'Avicel Water 2',
        'base_dir': 'E:/SMS-NMR/Data/Avicel/20251117_avicel_water_2/',
        'filename_prefix': 'CPMG_relaxorption_T2_avicel2_',
        'reference_file': 40,
        'default_start': 1,
        'default_end': 50
        },
        '8': {
        'name': 'Avicel Water 3',
        'base_dir': 'E:/SMS-NMR/Data/Avicel/20251117_avicel_water_3/',
        'filename_prefix': 'CPMG_relaxorption_T2_avicel3_',
        'reference_file': 40,
        'default_start': 1,
        'default_end': 50
        },
        '9': {
        'name': 'LiCl Dataset (0.5T, Gain=600dB)',
        'base_dir': 'E:/SMS-NMR/Data/LiCl (0.5 T, Gain=600dB)/20251203_LiCl_water/',
        'filename_prefix': 'CPMG_relaxorption_T2_LiCl_',
        'reference_file': 60,
        'default_start': 1,
        'default_end': 80
        },
        '10': {
        'name': 'LiCl Dataset (1211)',
        'base_dir': 'E:/SMS-NMR/Data/LiCl_1211/20251210_LiCl_water/',
        'filename_prefix': 'CPMG_relaxorption_T2_LiCl_',
        'reference_file': 70,
        'default_start': 1,
        'default_end': 150
        },
    }
    
    # User selection: Choose data source
    print("\n" + "="*80)
    print("SELECT DATA SOURCE")
    print("="*80)
    print("1. TNMR data (.tnt files)")
    print("2. Xigo data (.nmrdata files)")
    
    while True:
        try:
            choice = input("\nEnter choice (1 or 2): ").strip()
            if choice in ['1', '2']:
                data_source = int(choice)
                break
            else:
                print("Invalid choice. Please enter 1 or 2.")
        except KeyboardInterrupt:
            print("\nExiting...")
            sys.exit(0)
        except:
            print("Invalid input. Please enter 1 or 2.")
    
    all_data = []
    selected_dataset = None
    
    # User selection: Choose ILT method
    print("\n" + "="*80)
    print("SELECT ILT METHOD")
    print("="*80)
    print("1. RMEA1D (fast, default)")
    if ITAMED_AVAILABLE:
        print("2. ITAMeD (iterative, higher quality)")
    else:
        print("2. ITAMeD (not available - ITAMeD_python not found)")
    
    while True:
        try:
            ilt_choice = input("\nEnter choice (1 or 2, default=1): ").strip()
            if ilt_choice == '':
                ilt_method = 'rmea1d'
                break
            elif ilt_choice == '1':
                ilt_method = 'rmea1d'
                break
            elif ilt_choice == '2':
                if ITAMED_AVAILABLE:
                    ilt_method = 'itamed'
                    break
                else:
                    print("ITAMeD is not available. Please use RMEA1D (option 1) or install ITAMeD_python.")
            else:
                print("Invalid choice. Please enter 1 or 2.")
        except KeyboardInterrupt:
            print("\nExiting...")
            sys.exit(0)
        except:
            print("Invalid input. Please enter 1 or 2.")
    
    print(f"\nSelected ILT method: {ilt_method.upper()}")
    
    # CRITICAL: ITAMeD MUST use ITAMeD for lambda optimization
    # RMEA and ITAMeD use fundamentally different ILT approaches, so RMEA lambda values are not compatible
    if ilt_method == 'itamed':
        lambda_opt_method = 'itamed'  # Force ITAMeD to use ITAMeD for lambda optimization
        print("\n" + "="*80)
        print("LAMBDA OPTIMIZATION METHOD")
        print("="*80)
        print("ITAMeD method selected: Lambda optimization will use ITAMeD itself")
        print("  Note: RMEA lambda optimization is not compatible with ITAMeD")
        print("  Note: ITAMeD and RMEA use different ILT approaches, so lambda values are not interchangeable")
        if ITAMED_L2_AVAILABLE:
            print(f"  Note: Using L2 regularization (smooth, broad peaks)")
        else:
            print(f"  Note: L2 regularization not available, using L1 (sparse peaks)")
            print(f"        To use L2, ensure 'itamed_l2_version.py' is in the same directory as this script")
    else:
        lambda_opt_method = 'rmea1d'  # RMEA uses RMEA for lambda optimization
    
    # User selection: Choose whether to generate lambda variation plots
    print("\n" + "="*80)
    print("GENERATE LAMBDA VARIATION PLOTS?")
    print("="*80)
    print("Lambda variation plots show how different lambda values affect the T2 distribution.")
    print("1. No (skip lambda variation plots, default)")
    print("2. Yes (generate lambda variation plots - may take longer)")
    
    generate_lambda_variation = False  # Default
    while True:
        try:
            lambda_var_choice = input("\nEnter choice (1 or 2, default=1): ").strip()
            if lambda_var_choice == '':
                generate_lambda_variation = False
                break
            elif lambda_var_choice == '1':
                generate_lambda_variation = False
                break
            elif lambda_var_choice == '2':
                generate_lambda_variation = True
                break
            else:
                print("Invalid choice. Please enter 1 or 2.")
        except KeyboardInterrupt:
            print("\nExiting...")
            sys.exit(0)
        except:
            print("Invalid input. Please enter 1 or 2.")
    
    if generate_lambda_variation:
        print(f"\nLambda variation plots: ENABLED")
    else:
        print(f"\nLambda variation plots: DISABLED (skipping Step 7)")
    
    # User selection: Data truncation
    truncate_range = None
    if args.truncate:
        truncate_range = args.truncate
        print(f"\nData truncation from CLI: {truncate_range}")
    else:
        print("\n" + "="*80)
        print("DATA TRUNCATION")
        print("="*80)
        print("Do you want to truncate the data range?")
        print("Example: type '0-450' for 0 to 450ms, or press Enter to skip")
        
        while True:
            try:
                truncate_input = input("\nEnter truncation range (e.g., '0-450') or press Enter to skip: ").strip()
                if truncate_input == '':
                    truncate_range = None
                    print("No truncation applied.")
                    break
                else:
                    # Validate format: should be "start-end" with numbers
                    if '-' in truncate_input:
                        parts = truncate_input.split('-')
                        if len(parts) == 2:
                            try:
                                start_ms = float(parts[0].strip())
                                end_ms = float(parts[1].strip())
                                if start_ms < end_ms:
                                    truncate_range = truncate_input
                                    print(f"Data will be truncated to {start_ms}-{end_ms} ms")
                                    break
                                else:
                                    print("Error: Start time must be less than end time.")
                            except ValueError:
                                print("Error: Invalid format. Please use numbers like '0-450'")
                        else:
                            print("Error: Invalid format. Please use 'start-end' like '0-450'")
                    else:
                        print("Error: Invalid format. Please use 'start-end' like '0-450'")
            except KeyboardInterrupt:
                print("\nExiting...")
                sys.exit(0)
            except:
                print("Invalid input. Please try again.")
    
    if data_source == 1:
        # TNMR data processing
        print("\n" + "="*80)
        print("PROCESSING TNMR DATA")
        print("="*80)
        
        # Dataset selection menu
        print("\n" + "="*80)
        print("SELECT DATASET")
        print("="*80)
        print("Note: Command-line arguments (--base-dir, --filename-prefix, --reference-file)")
        print("      will override the selected dataset's defaults if provided.\n")
        for key, dataset in datasets.items():
            print(f"{key}. {dataset['name']}")
            print(f"   Base directory: {dataset['base_dir']}")
            print(f"   Filename prefix: {dataset['filename_prefix']}")
            print(f"   Reference file: {dataset['reference_file']}")
            print(f"   Default range: {dataset['default_start']} - {dataset['default_end']}")
            print()
        
        while True:
            try:
                dataset_choice = input("Enter dataset choice (1-{}): ".format(len(datasets))).strip()
                if dataset_choice in datasets:
                    selected_dataset = datasets[dataset_choice]
                    print(f"\nSelected: {selected_dataset['name']}")
                    break
                else:
                    print(f"Invalid choice. Please enter 1-{len(datasets)}.")
            except KeyboardInterrupt:
                print("\nExiting...")
                sys.exit(0)
            except:
                print(f"Invalid input. Please enter 1-{len(datasets)}.")
        
        # Set dataset parameters (CLI arguments override dataset defaults)
        if args.base_dir is None:
            base_dir = selected_dataset['base_dir']
        else:
            base_dir = args.base_dir
            # Ensure trailing slash
            if not base_dir.endswith('/') and not base_dir.endswith('\\'):
                base_dir += '/'
        
        if args.filename_prefix is None:
            filename_prefix = selected_dataset['filename_prefix']
        else:
            filename_prefix = args.filename_prefix
        
        # Update reference_file if dataset provides one and CLI doesn't override
        if args.reference_file is None:
            args.reference_file = selected_dataset['reference_file']
        
        # Update default start/end if not provided via CLI
        # For dataset 4, always use dataset defaults unless explicitly overridden
        if dataset_choice == '4':
            # For Urea dataset, use dataset defaults unless CLI explicitly provides different values
            # Check if user provided explicit start/end values (different from argparse defaults)
            if args.start == 1 and args.end == 188:
                # User didn't provide custom values, use dataset defaults
                args.start = selected_dataset['default_start']
                args.end = selected_dataset['default_end']
                print(f"[INFO] Dataset 4 (Urea): Using default range {args.start}-{args.end}")
            else:
                # User provided custom values, use them but warn if they seem wrong
                if args.start != selected_dataset['default_start'] or args.end != selected_dataset['default_end']:
                    print(f"[INFO] Dataset 4 (Urea): Using custom range {args.start}-{args.end} (dataset default is {selected_dataset['default_start']}-{selected_dataset['default_end']})")
        elif args.start == 1 and args.end == 188:  # Check if using defaults for other datasets
            args.start = selected_dataset['default_start']
            args.end = selected_dataset['default_end']

        # Special handling for dataset 4 (Urea Dataset): process all files (step=1) instead of jumping
        custom_step = None
        if dataset_choice == '4':
            # For Urea dataset, process all files regardless of mode
            custom_step = 1
            print(f"[INFO] Dataset 4 (Urea) selected: processing all files (step=1) instead of jumping")

        try:
            file_numbers = generate_file_numbers(args.start, args.end, args.mode, step=custom_step)
            print(f"[DEBUG] Generated file numbers: {file_numbers[:5]}...{file_numbers[-5:] if len(file_numbers) > 10 else file_numbers}")
        except ValueError as exc:
            print(f"[ERROR] {exc}")
            sys.exit(1)

        if not file_numbers:
            print("[ERROR] No file numbers selected. Adjust --start/--end values.")
            sys.exit(1)

        files_to_process = build_processing_plan(file_numbers, base_dir, 
                                                 filename_prefix=filename_prefix)
        # Calculate step_size for display (use custom_step if set, otherwise default logic)
        if custom_step is not None:
            step_size = custom_step
        else:
            step_size = 4 if args.mode == "jump4" else 1

        print(f"\nProcessing {len(files_to_process)} files (mode: {args.mode}, step={step_size})")
        print(f"File range: #{file_numbers[0]} → #{file_numbers[-1]}")
        print(f"File numbers: {describe_file_selection(file_numbers)}")
        print("Improved integration window detection: starts from minimum between peaks\n")
        
        # Step 1: Extract data from all files
        print("\n" + "="*80)
        print("STEP 1: EXTRACTING DATA FROM SELECTED FILES")
        print("="*80)
        
        for filename, fd, label in files_to_process:
            print("\n" + "="*80)
            print(f"PROCESSING FILE: {filename}")
            print("="*80)
            
            try:
                data = main(filename=filename, fd=fd)
                
                # Add verification that we got unique data
                print(f"\n[OK] Data extracted from {filename}")
                print(f"  - Number of echoes: {len(data['time_echoes'])}")
                print(f"  - First echo time: {data['time_echoes'][0]:.6f} ms" if len(data['time_echoes']) > 0 else "  - No echo times")
                print(f"  - Max peak integral: {np.max(data['peak_int']):.6f}")
                print(f"  - Phase angle: {data['ph0']} deg")
                
                # Update label to include scan information for Urea datasets
                if data.get('scan_number') is not None:
                    data['label'] = f"{label} (scan #{data['scan_number']})"
                else:
                    data['label'] = label
                all_data.append(data)
            except Exception as e:
                print(f"Error processing {filename}: {e}")
                print("Please ensure the file is loaded in TNMR before running the script.")
                print("Continuing to next file...\n")
    
    elif data_source == 2:
        # Xigo data processing
        print("\n" + "="*80)
        print("PROCESSING XIGO DATA")
        print("="*80)
        
        # Define Xigo datasets
        xigo_datasets = {
            '1': {
                'name': 'Water and Doped Water',
                'base_dir': 'E:/SMS-NMR/Data/water and doped water/',
                'files': [
                    # 20 mM cuso4 water (solid)
                    "E:/SMS-NMR/Data/water and doped water/20 mm cuso4 water.nmrdata",
                    # 10 mM cuso4 water (solid)
                    "E:/SMS-NMR/Data/water and doped water/10mm cuso4 water.nmrdata",
                    # 5 mM cuso4 water (solid)
                    "E:/SMS-NMR/Data/water and doped water/5 mm cuso4 water.nmrdata",
                    # 5 mM cuso4 water (T) (dotted)
                    "E:/SMS-NMR/Data/water and doped water/5 mm cuso4 water (T).nmrdata",
                    # 10 mM cuso4 water (T) (dotted)
                    "E:/SMS-NMR/Data/water and doped water/10 mm cuso4 water (T).nmrdata",
                    # 20 mM cuso4 water (T) (dotted)
                    "E:/SMS-NMR/Data/water and doped water/20 mm cuso4 water (T).nmrdata"
                ]
            },
            '2': {
                'name': 'Oil and Water',
                'base_dir': 'E:/SMS-NMR/Data/oil and water/',
                'files': [
                    # All water samples (solid) - grouped by type
                    "E:/SMS-NMR/Data/oil and water/experiment-T₂ measurement-0001 - water.nmrdata",
                    "E:/SMS-NMR/Data/oil and water/experiment-T₂ measurement-0002 - water.nmrdata",
                    "E:/SMS-NMR/Data/oil and water/experiment-T₂ measurement-0003 - water.nmrdata",
                    # All water+oil samples (solid) - grouped by type
                    "E:/SMS-NMR/Data/oil and water/experiment-T₂ measurement-0001 - water+oil.nmrdata",
                    "E:/SMS-NMR/Data/oil and water/experiment-T₂ measurement-0002 - water+oil.nmrdata",
                    "E:/SMS-NMR/Data/oil and water/experiment-T₂ measurement-0003 - water+oil.nmrdata",
                    # All oil samples (solid) - grouped by type
                    "E:/SMS-NMR/Data/oil and water/experiment-T₂ measurement-0001 - oil.nmrdata",
                    "E:/SMS-NMR/Data/oil and water/experiment-T₂ measurement-0002 - oil.nmrdata",
                    "E:/SMS-NMR/Data/oil and water/experiment-T₂ measurement-0003 - oil.nmrdata"
                ]
            },
            '3': {
                'name': 'Water and CuSO4',
                'base_dir': 'E:/SMS-NMR/Data/water and cuso4/',
                'files': [
                    # All 5 mM cuso4 water (solid) - grouped by type
                    "E:/SMS-NMR/Data/water and cuso4/5 mm cuso4 water-001.nmrdata",
                    "E:/SMS-NMR/Data/water and cuso4/5 mm cuso4 water-002.nmrdata",
                    "E:/SMS-NMR/Data/water and cuso4/5 mm cuso4 water-003.nmrdata",
                    # All 10 mM cuso4 water (solid) - grouped by type
                    "E:/SMS-NMR/Data/water and cuso4/10 mm cuso4 water-001.nmrdata",
                    "E:/SMS-NMR/Data/water and cuso4/10 mm cuso4 water-002.nmrdata",
                    "E:/SMS-NMR/Data/water and cuso4/10 mm cuso4 water-003.nmrdata",
                    # All 20 mM cuso4 water (solid) - grouped by type
                    "E:/SMS-NMR/Data/water and cuso4/20 mm cuso4 water-001.nmrdata",
                    "E:/SMS-NMR/Data/water and cuso4/20 mm cuso4 water-002.nmrdata",
                    "E:/SMS-NMR/Data/water and cuso4/20 mm cuso4 water-003.nmrdata",
                    # All 5 mM cuso4 water (T) (dotted) - grouped by type
                    "E:/SMS-NMR/Data/water and cuso4/5 mm cuso4 water-001 (T).nmrdata",
                    "E:/SMS-NMR/Data/water and cuso4/5 mm cuso4 water-002 (T).nmrdata",
                    "E:/SMS-NMR/Data/water and cuso4/5 mm cuso4 water-003 (T).nmrdata",
                    # All 10 mM cuso4 water (T) (dotted) - grouped by type
                    "E:/SMS-NMR/Data/water and cuso4/10 mm cuso4 water-001 (T).nmrdata",
                    "E:/SMS-NMR/Data/water and cuso4/10 mm cuso4 water-002 (T).nmrdata",
                    "E:/SMS-NMR/Data/water and cuso4/10 mm cuso4 water-003 (T).nmrdata",
                    "E:/SMS-NMR/Data/water and cuso4/10 mm cuso4 water-004 (T).nmrdata",
                    # All 20 mM cuso4 water (T) (dotted) - grouped by type
                    "E:/SMS-NMR/Data/water and cuso4/20 mm cuso4 water-001 (T).nmrdata",
                    "E:/SMS-NMR/Data/water and cuso4/20 mm cuso4 water-002 (T).nmrdata",
                    "E:/SMS-NMR/Data/water and cuso4/20 mm cuso4 water-003 (T).nmrdata",
                    # All water experiments (solid) - grouped by type
                    "E:/SMS-NMR/Data/water and cuso4/experiment-T₂ measurement-0001 - water.nmrdata",
                    "E:/SMS-NMR/Data/water and cuso4/experiment-T₂ measurement-0002 - water.nmrdata",
                    "E:/SMS-NMR/Data/water and cuso4/experiment-T₂ measurement-0003 - water.nmrdata",
                    # All 5 mM cuso4 only (solid) - grouped by type
                    "E:/SMS-NMR/Data/water and cuso4/5 mm cuso4-001.nmrdata",
                    "E:/SMS-NMR/Data/water and cuso4/5 mm cuso4-002.nmrdata",
                    "E:/SMS-NMR/Data/water and cuso4/5 mm cuso4-003.nmrdata",
                    # All 10 mM cuso4 only (solid) - grouped by type
                    "E:/SMS-NMR/Data/water and cuso4/10 mm cuso4-001.nmrdata",
                    "E:/SMS-NMR/Data/water and cuso4/10 mm cuso4-002.nmrdata",
                    "E:/SMS-NMR/Data/water and cuso4/10 mm cuso4-003.nmrdata",
                    # All 20 mM cuso4 only (solid) - grouped by type
                    "E:/SMS-NMR/Data/water and cuso4/20 mm cuso4-001.nmrdata",
                    "E:/SMS-NMR/Data/water and cuso4/20 mm cuso4-002.nmrdata",
                    "E:/SMS-NMR/Data/water and cuso4/20 mm cuso4-003.nmrdata"
                ]
            },
            '4': {
                'name': 'Cyclohexane and Doped Water',
                'base_dir': 'E:/SMS-NMR/Data/cycloh and doped water/',
                'files': [
                    # All dwater samples (solid) - grouped by type
                    "E:/SMS-NMR/Data/cycloh and doped water/experiment-T₂ measurement-0001_dwater.nmrdata",
                    "E:/SMS-NMR/Data/cycloh and doped water/experiment-T₂ measurement-0002_dwater.nmrdata",
                    "E:/SMS-NMR/Data/cycloh and doped water/experiment-T₂ measurement-0003_dwater.nmrdata",
                    # All dwater+cycloh samples (solid) - grouped by type
                    "E:/SMS-NMR/Data/cycloh and doped water/experiment-T₂ measurement-0001_dwater+cycloh.nmrdata",
                    "E:/SMS-NMR/Data/cycloh and doped water/experiment-T₂ measurement-0002_dwater+cycloh.nmrdata",
                    "E:/SMS-NMR/Data/cycloh and doped water/experiment-T₂ measurement-0003_dwater+cycloh.nmrdata"
                ]
            }
        }
        
        # Dataset selection menu
        print("\n" + "="*80)
        print("SELECT XIGO DATASET")
        print("="*80)
        for key, dataset in xigo_datasets.items():
            print(f"{key}. {dataset['name']}")
            print(f"   Files: {len(dataset['files'])}")
            print(f"   Directory: {dataset['base_dir']}")
            print()
        
        while True:
            try:
                dataset_choice = input("Enter dataset choice (1-{}): ".format(len(xigo_datasets))).strip()
                if dataset_choice in xigo_datasets:
                    selected_xigo_dataset = xigo_datasets[dataset_choice]
                    print(f"\nSelected: {selected_xigo_dataset['name']}")
                    break
                else:
                    print(f"Invalid choice. Please enter 1-{len(xigo_datasets)}.")
            except KeyboardInterrupt:
                print("\nExiting...")
                sys.exit(0)
            except:
                print(f"Invalid input. Please enter 1-{len(xigo_datasets)}.")
        
        xigo_files = selected_xigo_dataset['files']
        base_dir = selected_xigo_dataset['base_dir']
        
        # Set mode to "xigo" for compatibility with later code
        # args already parsed at the beginning, but we need to mark this as Xigo data
        args.mode = "xigo"
        step_size = 1  # All files are processed for Xigo
        
        # Ask user for relaxation type
        print("\nSelect relaxation type:")
        print("1. T1 relaxation (Mz signal)")
        print("2. T2 relaxation (Mxy signal)")
        while True:
            try:
                relax_choice = input("Enter choice (1 or 2, default=2): ").strip()
                if relax_choice == '':
                    relaxation_type = 2
                    break
                elif relax_choice in ['1', '2']:
                    relaxation_type = int(relax_choice)
                    break
                else:
                    print("Invalid choice. Please enter 1 or 2.")
            except KeyboardInterrupt:
                print("\nExiting...")
                sys.exit(0)
            except:
                print("Invalid input. Please enter 1 or 2.")
        
        print(f"\nProcessing {len(xigo_files)} Xigo files (relaxation type: {relaxation_type})")
        
        # Step 1: Extract data from all Xigo files
        print("\n" + "="*80)
        print("STEP 1: EXTRACTING DATA FROM XIGO FILES")
        print("="*80)
        
        for file_path in xigo_files:
            print("\n" + "="*80)
            print(f"PROCESSING FILE: {os.path.basename(file_path)}")
            print("="*80)
            
            try:
                data = extract_xigo_data(file_path, relaxation_type=relaxation_type)
                
                # Add verification that we got unique data
                print(f"\n[OK] Data extracted from {os.path.basename(file_path)}")
                print(f"  - Number of data points: {len(data['time_echoes'])}")
                print(f"  - First time point: {data['time_echoes'][0]:.6f} ms" if len(data['time_echoes']) > 0 else "  - No time points")
                print(f"  - Last time point: {data['time_echoes'][-1]:.6f} ms" if len(data['time_echoes']) > 0 else "  - No time points")
                print(f"  - Signal intensity (raw): {data['signal_intensity_raw']:.6f}")
                
                # Create label from filename
                filename_base = os.path.splitext(os.path.basename(file_path))[0]
                data['label'] = filename_base.replace(' ', '_')
                all_data.append(data)
            except Exception as e:
                print(f"Error processing {file_path}: {e}")
                import traceback
                traceback.print_exc()
                print("Continuing to next file...\n")
    
    if len(all_data) == 0:
        print("No data extracted. Exiting.")
        sys.exit(1)
    
    # For single file testing mode
    single_file_mode = (len(all_data) == 1)
    if single_file_mode:
        print("\n" + "="*80)
        print("SINGLE FILE TEST MODE")
        print("="*80)
        data = all_data[0]
        print(f"\nFile: {data['filename']}")
        print(f"Number of echoes detected: {len(data['time_echoes'])}")
        print(f"First echo time: {data['time_echoes'][0]:.6f} ms")
        print(f"Last echo time: {data['time_echoes'][-1]:.6f} ms")
        if len(data['time_echoes']) > 1:
            time_diff = (data['time_echoes'][1] - data['time_echoes'][0])
            print(f"Time between first 2 echoes: {time_diff:.6f} ms")
        print("\nProceeding to generate plots for verification...")
    
    # Check for duplicate data
    print("\n" + "="*80)
    print("CHECKING FOR DUPLICATE DATA")
    print("="*80)
    
    # Print summary for first and last few samples
    if len(all_data) > 10:
        print("Showing summary for first 3 and last 3 samples only...")
        for data in all_data[:3]:
            print_data_summary(data, label=data['label'])
        print("...")
        for data in all_data[-3:]:
            print_data_summary(data, label=data['label'])
        print(f"\n[INFO] Skipping duplicate check for large dataset ({len(all_data)} files)")
    else:
        for data in all_data:
            print_data_summary(data, label=data['label'])
        check_for_duplicates(all_data)
    
    # Apply data truncation if requested
    if truncate_range is not None:
        print("\n" + "="*80)
        print("APPLYING DATA TRUNCATION")
        print("="*80)
        
        # Parse truncation range
        parts = truncate_range.split('-')
        start_ms = float(parts[0].strip())
        end_ms = float(parts[1].strip())
        
        print(f"Truncating all datasets to time range: {start_ms}-{end_ms} ms")
        
        truncated_count = 0
        total_original_points = 0
        total_new_points = 0
        
        for idx, data in enumerate(all_data):
            original_length = len(data['time_echoes'])
            data, orig_len, new_len = truncate_dataset(data, start_ms, end_ms)
            all_data[idx] = data  # Update the dataset in the list
            
            truncated_count += 1
            total_original_points += orig_len
            total_new_points += new_len
            
            if idx < 3 or idx >= len(all_data) - 3:
                print(f"  {data['label']}: {orig_len} → {new_len} points (kept {new_len}/{orig_len} echoes)")
        
        print(f"\nTruncation complete:")
        print(f"  Processed {truncated_count} datasets")
        print(f"  Average points: {total_original_points/truncated_count:.1f} → {total_new_points/truncated_count:.1f}")
        print(f"  Time range: {start_ms}-{end_ms} ms")
    
    print("\n" + "="*80)
    print("STEP 2: DETERMINING GLOBAL OPTIMAL LAMBDA")
    print("="*80)
    
    # Use file #152 as the reference dataset (closest to experiment order ~150) for TNMR data
    # For Xigo data or single file mode, use first file or middle dataset
    # Allow override via command-line argument if provided
    if hasattr(args, 'reference_file') and args.reference_file is not None:
        reference_file_number = args.reference_file
    else:
        reference_file_number = 152  # Default value
    if single_file_mode:
        reference_index = 0
    else:
        # Try to find reference file by number (for TNMR data)
        reference_index = None
        try:
            reference_index = next(
                (
                    idx for idx, data in enumerate(all_data)
                    if '_' in data['label'] and len(data['label'].split('_')) > 1
                    and data['label'].split('_')[0] == 'Sample'
                    and int(data['label'].split('_')[1]) == reference_file_number
                ),
                None
            )
        except (ValueError, IndexError):
            pass
        
        if reference_index is None:
            print(f"[INFO] Using middle dataset as reference (file #{reference_file_number} not found or not applicable)")
            reference_index = len(all_data) // 2
    
    reference_data = all_data[reference_index]
    tau = reference_data['tau']
    
    # Try to extract file number for display
    try:
        if '_' in reference_data['label'] and reference_data['label'].split('_')[0] == 'Sample':
            actual_file_number = int(reference_data['label'].split('_')[1])
            print(f"[INFO] Using file #{actual_file_number} as reference for lambda optimization")
            if not single_file_mode and actual_file_number != reference_file_number:
                print(f"[WARNING] Requested file #{reference_file_number} but using file #{actual_file_number} instead")
        else:
            print(f"[INFO] Using dataset '{reference_data['label']}' as reference for lambda optimization")
    except (ValueError, IndexError):
        print(f"[INFO] Using dataset '{reference_data['label']}' as reference for lambda optimization")
    
    print(f"Using {reference_data['label']} ({reference_data['filename']}) as reference for lambda optimization...")
    print(f"  Reference dataset has {len(reference_data['time_echoes'])} data points")
    global_optimal_lambda = find_optimal_lambda(
        reference_data['time_echoes'],
        reference_data['peak_int_raw'],  # Use raw values (no normalization)
        tau,
        label=f"{reference_data['label']} (Global Reference)",
        save_dir=reference_data['fd'],
        method=ilt_method,
        lambda_opt_method=lambda_opt_method
    )
    
    print(f"\nGlobal optimal lambda determined: lambda = {global_optimal_lambda:.2e}")
    print(f"This lambda will be applied to all {len(all_data)} datasets.\n")
    
    # Step 3: Apply global lambda to all datasets
    print("\n" + "="*80)
    print("STEP 3: APPLYING GLOBAL LAMBDA TO ALL DATASETS")
    print("="*80)
    print(f"[DEBUG] ILT method selected: {ilt_method} (type: {type(ilt_method)})")
    print(f"[DEBUG] ITAMED_AVAILABLE: {ITAMED_AVAILABLE}")
    if ilt_method.lower() == 'itamed':
        print(f"[DEBUG] ITAMED_L2_AVAILABLE: {ITAMED_L2_AVAILABLE}")
    
    final_results = []
    for idx, data in enumerate(all_data):
        print(f"Analyzing {data['label']} with global lambda = {global_optimal_lambda:.2e} ({ilt_method.upper()})...")
        # Use raw peak integrals (no normalization)
        # Ensure method is passed correctly (normalize to lowercase)
        method_to_use = ilt_method.lower().strip() if isinstance(ilt_method, str) else 'rmea1d'
        print(f"  [DEBUG] Calling perform_ilt with method='{method_to_use}'")
        
        # Store method used for verification
        data['ilt_method_used'] = method_to_use
        
        f, mc = perform_ilt(data['time_echoes'], data['peak_int_raw'], tau, global_optimal_lambda, method=method_to_use)
        
        # Verification: Compare with RMEA1D if ITAMeD was supposed to be used (only for first dataset to avoid slowdown)
        # This helps diagnose if ITAMeD is actually running or silently falling back to RMEA1D
        if method_to_use == 'itamed' and idx == 0:
            print(f"  [VERIFY] ITAMeD was requested - comparing first dataset with RMEA1D to verify difference...")
            f_rmea, mc_rmea = rmea1d(data['time_echoes'], data['peak_int_raw'], tau, global_optimal_lambda)
            
            # Check if results are identical (within numerical precision)
            f_diff = np.abs(f - f_rmea)
            mc_diff = np.abs(mc - mc_rmea)
            max_f_diff = np.max(f_diff)
            max_mc_diff = np.max(mc_diff)
            mean_f_diff = np.mean(f_diff)
            mean_mc_diff = np.mean(mc_diff)
            
            print(f"  [VERIFY] Distribution difference: max={max_f_diff:.6e}, mean={mean_f_diff:.6e}")
            print(f"  [VERIFY] Fit difference: max={max_mc_diff:.6e}, mean={mean_mc_diff:.6e}")
            
            # Check if results are essentially identical (within 1e-10)
            if max_f_diff < 1e-10 and max_mc_diff < 1e-10:
                print(f"  [WARNING] ITAMeD and RMEA1D results are IDENTICAL (within 1e-10)!")
                print(f"  [WARNING] This suggests ITAMeD may not be running correctly or is falling back to RMEA1D")
            elif max_f_diff < 1e-6:
                print(f"  [WARNING] ITAMeD and RMEA1D results are VERY SIMILAR (max diff < 1e-6)")
                print(f"  [WARNING] This may indicate ITAMeD is not working as expected")
            else:
                print(f"  [OK] ITAMeD and RMEA1D results differ as expected")
            print(f"  [VERIFY] (Comparison only done for first dataset to avoid slowdown)")
        
        data['f'] = f
        data['mc'] = mc
        data['optimal_lambda'] = global_optimal_lambda
        
        # Use signal intensity from RAW (unnormalized) peak integrals (already calculated in main function)
        # This preserves absolute signal intensity values for comparison across files
        data['signal_intensity'] = data['signal_intensity_raw']
        
        final_results.append(data)
        print(f"Analysis complete for {data['label']} (Signal Intensity (raw) = {data['signal_intensity']:.6f})\n")

    # Extract file numbers (only for TNMR data with format "Sample_N")
    processed_file_numbers = []
    for idx, result in enumerate(final_results):
        try:
            # Try to extract file number from label (e.g., "Sample_60" -> 60)
            # Only for TNMR data that starts with "Sample_"
            if result['label'].startswith('Sample_') and '_' in result['label']:
                file_num = int(result['label'].split('_')[1])
                processed_file_numbers.append(file_num)
            else:
                # For Xigo data or other formats, use index
                processed_file_numbers.append(idx + 1)
        except (ValueError, IndexError):
            # If extraction fails, use index
            processed_file_numbers.append(idx + 1)
    
    # Step 4: Generate all plots
    print("\n" + "="*80)
    print("STEP 4: GENERATING PLOTS")
    print("="*80)
    
    # Create plots directory with method-specific subfolder
    # Format: plots/{ilt_method}_{lambda_opt_method}/
    # Get base_dir from first result if not already set (for Xigo data)
    if 'base_dir' not in locals() or base_dir is None:
        if len(final_results) > 0:
            base_dir = final_results[0].get('fd', os.getcwd())
        else:
            base_dir = os.getcwd()
    
    method_subfolder = f"{ilt_method}_{lambda_opt_method}"
    plots_dir = os.path.join(base_dir, "plots", method_subfolder)
    os.makedirs(plots_dir, exist_ok=True)
    print(f"Plots will be saved to: {plots_dir}")
    print(f"  Method: {ilt_method.upper()} (ILT), {lambda_opt_method.upper()} (lambda optimization)")
    
    # Create combined summary figure with all datasets as subplots
    # Split into multiple pages if too many datasets (to avoid exceeding matplotlib size limits)
    num_datasets = len(final_results)
    max_rows_per_page = 12  # Maximum rows per page to avoid image size errors
    num_pages = (num_datasets + max_rows_per_page - 1) // max_rows_per_page
    
    print(f"Generating summary plots: {num_datasets} samples split across {num_pages} page(s)...")
    
    colors = plt.cm.tab10(np.linspace(0, 1, num_datasets))
    
    for page_num in range(num_pages):
        start_idx = page_num * max_rows_per_page
        end_idx = min(start_idx + max_rows_per_page, num_datasets)
        rows_this_page = end_idx - start_idx
        
        print(f"  Creating page {page_num + 1}/{num_pages} (samples {start_idx + 1}-{end_idx})...")
        
        fig, axes = plt.subplots(rows_this_page, 5, figsize=(28, 5.5*rows_this_page))
        
        # Ensure axes is 2D (even for single row)
        if rows_this_page == 1:
            axes = axes.reshape(1, -1)
        
        for local_row_idx, global_idx in enumerate(range(start_idx, end_idx)):
            result = final_results[global_idx]
            color = colors[global_idx]
            row_idx = local_row_idx
            
            # Plot 1: Raw FID (skip for Xigo data)
            if result['rfid'] is not None and result['ifid'] is not None:
                idx_limit = min(len(result['time_arr']) // 10, len(result['time_arr']))
                axes[row_idx, 0].plot(result['time_arr'][:idx_limit], result['rfid'][:idx_limit], 
                                     color=color, linewidth=1.5, label='Real', alpha=0.8)
                axes[row_idx, 0].plot(result['time_arr'][:idx_limit], result['ifid'][:idx_limit], 
                                     color='gray', linewidth=1.5, label='Imag', alpha=0.6)
                axes[row_idx, 0].set_xlabel('Time (s)')
                axes[row_idx, 0].set_ylabel('Amplitude')
                axes[row_idx, 0].set_title(f'{result["label"]} - Raw FID')
                axes[row_idx, 0].legend(fontsize=8)
                axes[row_idx, 0].grid(True, alpha=0.3)
            else:
                # For Xigo data, show time vs signal instead
                axes[row_idx, 0].plot(result['time_echoes'], result['peak_int'], 
                                     'o-', color=color, linewidth=1.5, markersize=3, alpha=0.8)
                axes[row_idx, 0].set_xlabel('Time (ms)')
                axes[row_idx, 0].set_ylabel('Normalized Signal')
                axes[row_idx, 0].set_title(f'{result["label"]} - Signal Decay')
                axes[row_idx, 0].grid(True, alpha=0.3)
            
            # Plot 2: Phased FID (skip for Xigo data)
            if result['rfid_phased'] is not None and result['ifid_phased'] is not None:
                idx_limit = min(len(result['time_arr']) // 10, len(result['time_arr']))
                axes[row_idx, 1].plot(result['time_arr'][:idx_limit], result['rfid_phased'][:idx_limit], 
                                     color=color, linewidth=1.5, label='Real', alpha=0.8)
                axes[row_idx, 1].plot(result['time_arr'][:idx_limit], result['ifid_phased'][:idx_limit], 
                                     color='gray', linewidth=1.5, label='Imag', alpha=0.6)
                axes[row_idx, 1].set_xlabel('Time (s)')
                axes[row_idx, 1].set_ylabel('Amplitude')
                axes[row_idx, 1].set_title(f'{result["label"]} - Phased FID (ph0 = {result["ph0"]}°)')
                axes[row_idx, 1].legend(fontsize=8)
                axes[row_idx, 1].grid(True, alpha=0.3)
            else:
                # For Xigo data, show raw signal intensity info
                axes[row_idx, 1].text(0.5, 0.5, f'Signal Intensity (raw):\n{result["signal_intensity_raw"]:.6f}\n\nData Points: {len(result["time_echoes"])}\nTime Range: {result["time_echoes"][0]:.2f} - {result["time_echoes"][-1]:.2f} ms',
                                     transform=axes[row_idx, 1].transAxes, 
                                     fontsize=10, ha='center', va='center',
                                     bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
                axes[row_idx, 1].set_title(f'{result["label"]} - Data Info')
                axes[row_idx, 1].axis('off')
            
            # Plot 3: First 5 echoes with integration regions
            # Use the same method as actual integration - show calculated echo centers and windows
            nechoes_plot = 5
            
            # Check if this is TNMR data (has FID) or Xigo data
            if result['rfid_phased'] is not None:
                # TNMR data - use actual integration windows
                signal = result['rfid_phased']
                time_arr = result['time_arr']
                echo_pts = result['exp_params'].get('echo_pts', 16)
                center_idxs = result.get('center_idxs', [])
                start_idxs = result.get('start_idxs', [])
                end_idxs = result.get('end_idxs', [])
                
                if len(center_idxs) >= nechoes_plot:
                    # Use actual calculated echo centers and integration windows
                    num_peaks_to_plot = min(nechoes_plot, len(center_idxs))
                    plot_centers = center_idxs[:num_peaks_to_plot]
                    plot_starts = start_idxs[:num_peaks_to_plot] if len(start_idxs) >= num_peaks_to_plot else []
                    plot_ends = end_idxs[:num_peaks_to_plot] if len(end_idxs) >= num_peaks_to_plot else []
                    
                    # Determine plot range
                    first_center = plot_centers[0]
                    last_center = plot_centers[-1]
                    buffer_points = max(echo_pts, 50)
                    idx_start = max(min(plot_starts) if len(plot_starts) > 0 else first_center - buffer_points, 0)
                    idx_end = min(max(plot_ends) if len(plot_ends) > 0 else last_center + buffer_points, len(time_arr))
                    
                    # Plot signal
                    axes[row_idx, 2].plot(time_arr[idx_start:idx_end], 
                                         signal[idx_start:idx_end], 
                                         color=color, linewidth=1.5, alpha=0.7, label='Signal')
                    
                    peak_colors = ['red', 'blue', 'green', 'orange', 'purple']
                    
                    for i, center in enumerate(plot_centers):
                        peak_color = peak_colors[i % len(peak_colors)]
                        
                        # Use actual integration windows if available, otherwise calculate
                        if i < len(plot_starts) and i < len(plot_ends):
                            window_start = plot_starts[i]
                            window_end = plot_ends[i]
                        else:
                            # Fallback: calculate window as in integration method
                            window_start = max(center - (echo_pts // 2) - 1, 0)
                            window_end = min(center + (echo_pts // 2) + 1, len(signal))
                    
                        time_start = time_arr[window_start]
                        # Include boundary point (window_end) to show contiguous curves
                        # window_end is the start of next window, so include it for visual continuity
                        plot_end = min(window_end + 1, len(time_arr))  # Include boundary point
                        time_end = time_arr[min(window_end, len(time_arr) - 1)]
                        
                        # Plot integration region - include boundary point for visual continuity
                        # This ensures the colored curves connect seamlessly
                        axes[row_idx, 2].plot(time_arr[window_start:plot_end], 
                                             signal[window_start:plot_end],
                                             color=peak_color, linewidth=4, alpha=0.95, 
                                             label=f'Peak {i+1} region' if i < len(peak_colors) else 'Integrated region', 
                                             zorder=10)
                        # For axvspan, use window_end (which is the start of next window) to show contiguous windows
                        axes[row_idx, 2].axvspan(time_start, time_end, 
                                                 alpha=0.2, color=peak_color, zorder=9)
                        
                        # Mark echo center
                        axes[row_idx, 2].plot(time_arr[center], 
                                             signal[center],
                                             'ko', markersize=8, markeredgewidth=2,
                                             markeredgecolor='white', zorder=12,
                                             label='Peak center' if i == 0 else '')
                    
                    axes[row_idx, 2].set_xlabel('Time (s)', fontsize=9)
                    axes[row_idx, 2].set_ylabel('Amplitude', fontsize=9)
                    axes[row_idx, 2].set_title(f'{result["label"]} - First {nechoes_plot} Echoes (zoomed)', fontsize=10)
                    axes[row_idx, 2].legend(fontsize=8, loc='upper right')
                    axes[row_idx, 2].grid(True, alpha=0.3)
                else:
                    axes[row_idx, 2].text(0.5, 0.5, f'Not enough echoes\n(only {len(center_idxs)} available)', 
                                         transform=axes[row_idx, 2].transAxes, 
                                         ha='center', va='center', fontsize=12)
                    axes[row_idx, 2].set_title(f'{result["label"]} - Insufficient Echoes', fontsize=10)
                    axes[row_idx, 2].grid(True, alpha=0.3)
            else:
                # Xigo data - plot first portion of decay curve
                # Show first 5% of data points or first 50 points, whichever is smaller
                signal_xigo = result['peak_int']
                time_arr_xigo = result['time_echoes']  # Use time_echoes for Xigo
                num_points_to_show = min(50, max(10, len(signal_xigo) // 20))
                axes[row_idx, 2].plot(time_arr_xigo[:num_points_to_show], signal_xigo[:num_points_to_show], 
                                     'o-', color=color, linewidth=1.5, markersize=3, alpha=0.8, label='Signal decay')
                axes[row_idx, 2].set_xlabel('Time (ms)', fontsize=9)
                axes[row_idx, 2].set_ylabel('Normalized Signal', fontsize=9)
                axes[row_idx, 2].set_title(f'{result["label"]} - First {num_points_to_show} Data Points', fontsize=10)
                axes[row_idx, 2].legend(fontsize=8, loc='upper right')
                axes[row_idx, 2].grid(True, alpha=0.3)
            
            # Plot 4: Echo decay and ILT fit
            # Use raw peak integrals (no normalization, no scaling)
            peak_int_raw = result['peak_int_raw']
            # ILT fit (mc) is already in absolute units since we use raw input
            mc_absolute = result['mc']
            
            axes[row_idx, 3].plot(result['time_echoes'], peak_int_raw, 'ko', markersize=4, label='Exp. data')
            axes[row_idx, 3].plot(result['time_echoes'], mc_absolute, color=color, linewidth=2, label='ILT fit')
            axes[row_idx, 3].set_xlabel('Time (ms)')
            axes[row_idx, 3].set_ylabel('Amplitude')
            axes[row_idx, 3].set_title(f'{result["label"]} - Echo Decay')
            axes[row_idx, 3].legend(fontsize=8)
            axes[row_idx, 3].grid(True, alpha=0.3)
            # Ensure full decay is shown - no xlim restriction
            if len(result['time_echoes']) > 0:
                axes[row_idx, 3].set_xlim([0, result['time_echoes'][-1] * 1.05])  # Show full range with 5% margin
            
            # Plot 5: T2 distribution
            # T2 distribution (f) is already in absolute units since we use raw input (no normalization)
            axes[row_idx, 4].semilogx(tau, result['f'], color=color, linewidth=2, label=result['label'])
            axes[row_idx, 4].set_xlabel('T2 Relaxation Time (ms)', fontsize=10)
            axes[row_idx, 4].set_ylabel('Amplitude', fontsize=10)
            axes[row_idx, 4].set_title(f'{result["label"]} - T2 Distribution', fontweight='bold')
            axes[row_idx, 4].set_xlim([1, 100000])
            
            # Find and mark peaks
            peaks_dist, _ = find_peaks(result['f'], height=np.max(result['f']) * 0.1)
            if len(peaks_dist) > 0:
                for peak_idx in peaks_dist:
                    peak_tau = tau[peak_idx]
                    axes[row_idx, 4].axvline(x=peak_tau, color='r', linestyle='--', linewidth=1, alpha=0.7)
            
            axes[row_idx, 4].grid(True, which='both', alpha=0.3)
            axes[row_idx, 4].legend(fontsize=8)
    
        # Add title and save this page
        page_suffix = f"_page{page_num + 1}" if num_pages > 1 else ""
        fig.suptitle(f'Summary: Samples {start_idx + 1}-{end_idx} (λ = {global_optimal_lambda:.2e}, Method = {ilt_method.upper()})', 
                     fontsize=16, fontweight='bold', y=0.995)
        plt.tight_layout(rect=[0, 0, 1, 0.99])
        
        # Save combined figure (don't display)
        save_loc_summary = os.path.join(plots_dir, f"summary_all_samples{page_suffix}.jpg")
        plt.savefig(save_loc_summary, dpi=300, bbox_inches="tight")
        print(f"  Summary figure page {page_num + 1} saved: {save_loc_summary}")
        plt.close(fig)  # Close without showing
    
    # Save experimental details for each
    for result in final_results:
        save_loc_txt = os.path.join(result['fd'], f"{result['filename']}_exp_details.txt")
        with open(save_loc_txt, "w") as f:
            for key, value in result['exp_params'].items():
                f.write(f"{key}: {value}\n")
            f.write(f"\nglobal_optimal_lambda: {global_optimal_lambda:.2e}\n")
        print(f"Experimental details saved: {save_loc_txt}")
    
    # Step 5: Add time information and generate Signal Intensity plot
    print("\n" + "="*80)
    print("STEP 5: ADDING TIME INFORMATION AND GENERATING SIGNAL INTENSITY PLOT")
    print("="*80)
    
    # Check if this is TNMR data (has FID data) or Xigo data
    is_tnmr_data = any(result.get('rfid_phased') is not None for result in final_results)
    
    # Try to load timestamps from CSV file for TNMR data
    timestamps_dict = None
    first_timestamp = None
    
    if is_tnmr_data and data_source == 1:
        # TNMR data: Try to load timestamps from CSV file
        # Look for timestamp CSV file in base_dir (common names: timestamps.csv, file_timestamps.csv, etc.)
        timestamp_file_candidates = [
            os.path.join(base_dir, 'timestamps.csv'),
            os.path.join(base_dir, 'file_timestamps.csv'),
            os.path.join(base_dir, 'timestamp.csv'),
            os.path.join(base_dir, 'file_times.csv'),
        ]
        
        timestamp_file = None
        for candidate in timestamp_file_candidates:
            if os.path.exists(candidate):
                timestamp_file = candidate
                break
        
        if timestamp_file:
            print(f"\nFound timestamp file: {timestamp_file}")
            try:
                timestamps_dict = load_timestamps_from_csv(timestamp_file, filename_prefix)
                if len(timestamps_dict) > 0:
                    # Get the first timestamp (earliest) to calculate elapsed time
                    sorted_timestamps = sorted(timestamps_dict.items(), key=lambda x: x[1])
                    first_file_num, first_timestamp = sorted_timestamps[0]
                    print(f"  Using file #{first_file_num} as reference (timestamp: {first_timestamp})")
                    print(f"  Calculating elapsed time from first timestamp")
            except Exception as e:
                print(f"  WARNING: Could not load timestamps from {timestamp_file}: {e}")
                print(f"  Falling back to echo-time-based calculation (412 seconds per file)")
                timestamps_dict = None
        else:
            print(f"\nNo timestamp file found in {base_dir}")
            print(f"  Looked for: {', '.join([os.path.basename(c) for c in timestamp_file_candidates])}")
            print(f"  Using echo-time-based calculation (412 seconds per file)")
    
    # Add time information to each result
    for i, result in enumerate(final_results):
        # Try to extract file number from label (for TNMR data with format "Sample_N")
        try:
            if '_' in result['label'] and result['label'].split('_')[0] == 'Sample':
                file_num = int(result['label'].split('_')[1])
                
                # Use timestamp if available
                if timestamps_dict is not None and file_num in timestamps_dict:
                    # Calculate elapsed time from first timestamp
                    current_timestamp = timestamps_dict[file_num]
                    elapsed_time = (current_timestamp - first_timestamp).total_seconds()
                    result['time_seconds'] = elapsed_time
                else:
                    # Fallback to old method: Each experiment is 412 seconds apart
                    result['time_seconds'] = (file_num - 1) * 412  # Time in seconds
            else:
                # For Xigo data or other formats, use index (assuming sequential measurements)
                result['time_seconds'] = i * 412  # Use index-based time
        except (ValueError, IndexError):
            # Fallback: use index-based time
            result['time_seconds'] = i * 412
        
        result['time_minutes'] = result['time_seconds'] / 60.0  # Convert to minutes
        result['time_label'] = f"{result['time_minutes']:.1f} min"
    
    # Helper function to extract concentration from label
    def extract_concentration(label):
        """Extract concentration (in mM) from label string.
        Handles formats like: '5 mm', '5mm', '5_mm', '10mm', etc.
        """
        # Match digits followed by optional whitespace/underscore and 'mm'
        match = re.search(r'(\d+)[\s_]*mm', label, re.IGNORECASE)
        if match:
            return int(match.group(1))
        return None
    
    # Helper function to get color based on concentration
    def get_concentration_color(concentration):
        """Get color based on concentration: 5mm=blue, 10mm=green, 20mm=red."""
        if concentration == 5:
            return 'tab:blue'
        elif concentration == 10:
            return 'tab:green'
        elif concentration == 20:
            return 'tab:red'
        else:
            return 'tab:gray'
    
    # Check if this is Xigo data (no FID data available)
    is_xigo_data = any(result.get('rfid_phased') is None for result in final_results)
    
    # Generate Signal Intensity plot
    print("Generating Signal Intensity plot...")
    signal_intensities = [result['signal_intensity'] for result in final_results]
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    if is_xigo_data:
        # Xigo data: plot by sample with concentration-based colors
        labels = [result['label'] for result in final_results]
        x_positions = np.arange(len(final_results))
        
        # Get colors based on concentration
        colors_list = []
        for result in final_results:
            conc = extract_concentration(result['label'])
            colors_list.append(get_concentration_color(conc) if conc else 'tab:gray')
        
        bars = ax.bar(x_positions, signal_intensities, color=colors_list, alpha=0.7, 
                     label='Signal Intensity (avg of first 5 peaks, raw values)')
        
        # Add concentration labels on bars
        for i, (bar, result) in enumerate(zip(bars, final_results)):
            conc = extract_concentration(result['label'])
            is_T_variant = '(T)' in result['label'] or '_T' in result['label']
            if conc is not None:
                label_text = f"{conc} mM"
                if is_T_variant:
                    label_text += " (T)"
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height(),
                       label_text, ha='center', va='bottom', fontsize=9, fontweight='bold')
        
        ax.set_xticks(x_positions)
        ax.set_xticklabels([f"Sample {i+1}" for i in range(len(final_results))], fontsize=9)
        ax.set_xlabel('Sample', fontsize=12)
        ax.set_ylabel('Signal Intensity (raw, absolute values)', fontsize=12)
        ax.set_title('NMR Signal Intensity by Sample\n(Average of First 5 Integrated Peak Areas - Raw Values)', 
                     fontsize=14, fontweight='bold')
        
        # Add legend for concentrations
        from matplotlib.patches import Patch
        legend_elements = [
            Patch(facecolor='tab:blue', alpha=0.7, label='5 mM'),
            Patch(facecolor='tab:green', alpha=0.7, label='10 mM'),
            Patch(facecolor='tab:red', alpha=0.7, label='20 mM')
        ]
        ax.legend(handles=legend_elements, fontsize=9, loc='upper right', title='Concentration')
        
        # Add note about (T) variant
        ax.text(0.98, 0.02, '(T) = CuSO4 in capillary tube', transform=ax.transAxes, 
               fontsize=9, ha='right', va='bottom', 
               bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.7))
    else:
        # TNMR data: plot over time
        time_minutes = [result['time_minutes'] for result in final_results]
        ax.plot(time_minutes, signal_intensities, 'o-', linewidth=2, markersize=6, 
                color='tab:blue', label='Signal Intensity (avg of first 5 peaks, raw values)')
        ax.set_xlabel('Time (minutes)', fontsize=12)
        ax.set_ylabel('Signal Intensity (raw, absolute values)', fontsize=12)
        ax.set_title('NMR Signal Intensity Over Time\n(Average of First 5 Integrated Peak Areas - Raw Values)', 
                     fontsize=14, fontweight='bold')
        ax.legend(fontsize=10, loc='upper right')
    
    ax.grid(True, alpha=0.3)
    
    # Add some statistics
    mean_intensity = np.mean(signal_intensities)
    std_intensity = np.std(signal_intensities)
    # Removed red dotted average line as requested
    
    # Add text box with statistics
    textstr = f'Mean: {mean_intensity:.4f}\nStd: {std_intensity:.4f}\nMin: {min(signal_intensities):.4f}\nMax: {max(signal_intensities):.4f}'
    props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
    ax.text(0.02, 0.98, textstr, transform=ax.transAxes, fontsize=10,
            verticalalignment='top', bbox=props)
    
    plt.tight_layout()
    
    plot_name = "signal_intensity_by_concentration.jpg" if is_xigo_data else "signal_intensity_over_time.jpg"
    signal_intensity_save_loc = os.path.join(plots_dir, plot_name)
    plt.savefig(signal_intensity_save_loc, dpi=300, bbox_inches="tight")
    print(f"Signal Intensity plot saved: {signal_intensity_save_loc}")
    plt.close()
    
    # Step 6: Generate 2D stacked T2 distribution plot
    print("\n" + "="*80)
    print("STEP 6: GENERATING 2D STACKED T2 DISTRIBUTION PLOT")
    print("="*80)
    
    # is_xigo_data already defined above
    
    # Create 2D stacked plot
    fig, ax = plt.subplots(figsize=(14, 16))
    
    # Find maximum intensity for offset calculation
    # NOTE: No normalization applied - using raw intensities from ILT analysis
    max_intensity = max([np.max(result['f']) for result in final_results])
    
    # Plot with vertical offset for each sample
    # Reduced offset_factor to make peaks more visible and compact
    offset_factor = 0.08  # Reduced from 0.12 to make peaks more obvious
    
    # Check which Xigo dataset this is - needed for legend formatting and color/style mapping
    dataset_number = None
    if is_xigo_data and len(final_results) > 0:
        result_dir = final_results[0].get('fd', '')
        if result_dir:
            if 'water and cuso4' in result_dir.lower():
                dataset_number = 3
            elif 'water and doped water' in result_dir.lower():
                dataset_number = 1
            elif 'oil and water' in result_dir.lower():
                dataset_number = 2
            elif 'cycloh and doped water' in result_dir.lower():
                dataset_number = 4
    
    if is_xigo_data:
        # Xigo data: use sample-type-based colors and labels
        # Helper function to extract sample type from filename/label
        def extract_sample_type(label, filename):
            """Extract sample type (water, oil, water+oil, dwater, dwater+cycloh, etc.)"""
            label_lower = label.lower()
            filename_lower = filename.lower()
            
            # Check for oil and water combinations
            if 'water+oil' in label_lower or 'water+oil' in filename_lower:
                return 'water+oil'
            elif 'dwater+cycloh' in label_lower or 'dwater+cycloh' in filename_lower:
                return 'dwater+cycloh'
            elif 'oil' in label_lower or 'oil' in filename_lower:
                return 'oil'
            elif 'dwater' in label_lower or 'dwater' in filename_lower:
                return 'dwater'
            elif 'water' in label_lower or 'water' in filename_lower:
                return 'water'
            else:
                return 'unknown'
        
        # Helper function to get color based on sample type
        def get_sample_type_color(sample_type):
            """Get color based on sample type"""
            color_map = {
                'water': 'tab:blue',
                'oil': 'tab:orange',
                'water+oil': 'tab:green',
                'dwater': 'tab:cyan',
                'dwater+cycloh': 'tab:purple',
                'unknown': 'tab:gray'
            }
            return color_map.get(sample_type, 'tab:gray')
        
        # Helper function to get color and style for dataset 3 (Water and CuSO4)
        def get_dataset3_color_and_style(filename, label):
            """Get specific color and line style for dataset 3 based on filename pattern"""
            filename_lower = filename.lower()
            label_lower = label.lower()
            
            # Check if it's a (T) variant
            is_T_variant = '(T)' in filename or '(T)' in label or ' (T)' in filename
            
            # RGB colors converted to 0-1 range (as specified by user)
            color_20mM = (255/255, 165/255, 0/255)   # Orange
            color_10mM = (58/255, 130/255, 169/255)  # Blue
            color_5mM = (13/255, 8/255, 135/255)     # Dark blue/purple
            color_water = (30/255, 30/255, 30/255)   # Dark gray
            
            # Extract base filename for label
            base_filename = os.path.basename(filename).replace('.nmrdata', '')
            
            # Determine color based on concentration and sample type
            if '20 mm cuso4 water' in filename_lower or '20 mm cuso4 water' in label_lower:
                color = color_20mM
                label_text = base_filename
            elif '10 mm cuso4 water' in filename_lower or '10 mm cuso4 water' in label_lower:
                color = color_10mM
                label_text = base_filename
            elif '5 mm cuso4 water' in filename_lower or '5 mm cuso4 water' in label_lower:
                color = color_5mM
                label_text = base_filename
            elif 'experiment' in filename_lower and 'water' in filename_lower:
                color = color_water
                # Format: "Exp-0001: water"
                filename_clean = base_filename.replace('experiment-T₂ measurement-', '')
                if ' - ' in filename_clean:
                    parts = filename_clean.split(' - ')
                    if len(parts) >= 2:
                        exp_num = parts[0].split('-')[-1] if '-' in parts[0] else parts[0]
                        label_text = f"Exp-{exp_num}: water"
                    else:
                        label_text = filename_clean
                else:
                    label_text = filename_clean.replace('_', ' ')
            elif '20 mm cuso4' in filename_lower and 'water' not in filename_lower:
                color = color_20mM
                label_text = base_filename
            elif '10 mm cuso4' in filename_lower and 'water' not in filename_lower:
                color = color_10mM
                label_text = base_filename
            elif '5 mm cuso4' in filename_lower and 'water' not in filename_lower:
                color = color_5mM
                label_text = base_filename
            else:
                # Fallback to default
                conc = extract_concentration(label)
                if conc is not None:
                    if conc == 20:
                        color = color_20mM
                    elif conc == 10:
                        color = color_10mM
                    elif conc == 5:
                        color = color_5mM
                    else:
                        color = get_concentration_color(conc)
                else:
                    color = get_sample_type_color(extract_sample_type(label, filename))
                label_text = base_filename
            
            # Line style: solid for regular, dotted for (T) variants
            linestyle = ':' if is_T_variant else '-'
            
            return color, linestyle, label_text
        
        # Helper function to get color and style for dataset 1 (Water and Doped Water)
        def get_dataset1_color_and_style(filename, label):
            """Get specific color and line style for dataset 1 based on filename pattern"""
            filename_lower = filename.lower()
            label_lower = label.lower()
            
            # Check if it's a (T) variant
            is_T_variant = '(T)' in filename or '(T)' in label or ' (T)' in filename
            
            # RGB colors converted to 0-1 range (same as dataset 3)
            color_20mM = (255/255, 165/255, 0/255)   # Orange
            color_10mM = (58/255, 130/255, 169/255)  # Blue
            color_5mM = (13/255, 8/255, 135/255)     # Dark blue/purple
            
            # Extract base filename for label
            base_filename = os.path.basename(filename).replace('.nmrdata', '')
            
            # Determine color based on concentration
            if '20 mm cuso4' in filename_lower or '20 mm cuso4' in label_lower:
                color = color_20mM
            elif '10 mm cuso4' in filename_lower or '10mm cuso4' in filename_lower:
                color = color_10mM
            elif '5 mm cuso4' in filename_lower or '5 mm cuso4' in label_lower:
                color = color_5mM
            else:
                # Fallback
                conc = extract_concentration(label)
                if conc == 20:
                    color = color_20mM
                elif conc == 10:
                    color = color_10mM
                elif conc == 5:
                    color = color_5mM
                else:
                    color = get_concentration_color(conc) if conc else (0.5, 0.5, 0.5)
            
            label_text = base_filename
            
            # Line style: solid for regular, dotted for (T) variants
            linestyle = ':' if is_T_variant else '-'
            
            return color, linestyle, label_text
        
        # Helper function to get color and style for dataset 2 (Oil and Water)
        def get_dataset2_color_and_style(filename, label):
            """Get specific color and line style for dataset 2 based on filename pattern"""
            filename_lower = filename.lower()
            label_lower = label.lower()
            
            # Use same three colors as other datasets
            color_20mM = (255/255, 165/255, 0/255)   # Orange
            color_10mM = (58/255, 130/255, 169/255)  # Mid Blue
            color_5mM = (13/255, 8/255, 135/255)     # Indigo
            
            # Extract base filename for label
            base_filename = os.path.basename(filename).replace('.nmrdata', '')
            
            # Determine color based on sample type (map to the three colors)
            # water → color_5mM (Indigo), water+oil → color_10mM (Mid Blue), oil → color_20mM (Orange)
            if 'water+oil' in filename_lower or 'water+oil' in label_lower:
                color = color_10mM  # Mid Blue for water+oil
            elif 'oil' in filename_lower and 'water' not in filename_lower:
                color = color_20mM  # Orange for oil
            elif 'water' in filename_lower:
                color = color_5mM  # Indigo for water
            else:
                color = color_5mM  # Default to Indigo
            
            # Format label: "Exp-0001: water", "Exp-0001: water+oil", etc.
            filename_clean = base_filename.replace('experiment-T₂ measurement-', '')
            if ' - ' in filename_clean:
                parts = filename_clean.split(' - ')
                if len(parts) >= 2:
                    exp_num = parts[0].split('-')[-1] if '-' in parts[0] else parts[0]
                    sample_desc = parts[1].replace('_', ' ')
                    label_text = f"Exp-{exp_num}: {sample_desc}"
                else:
                    label_text = filename_clean
            else:
                label_text = filename_clean.replace('_', ' ')
            
            # All samples use solid lines
            linestyle = '-'
            
            return color, linestyle, label_text
        
        # Helper function to get color and style for dataset 4 (Cyclohexane and Doped Water)
        def get_dataset4_color_and_style(filename, label):
            """Get specific color and line style for dataset 4 based on filename pattern"""
            filename_lower = filename.lower()
            label_lower = label.lower()
            
            # Use same three colors as other datasets
            color_20mM = (255/255, 165/255, 0/255)   # Orange
            color_10mM = (58/255, 130/255, 169/255)  # Blue
            color_5mM = (13/255, 8/255, 135/255)     # Dark blue/purple
            
            # Extract base filename for label
            base_filename = os.path.basename(filename).replace('.nmrdata', '')
            
            # Determine color based on sample type (map to the three colors)
            if 'dwater+cycloh' in filename_lower or 'dwater+cycloh' in label_lower:
                color = color_20mM  # Yellow-green for dwater+cycloh
            elif 'dwater' in filename_lower:
                color = color_5mM  # Dark blue/purple for dwater
            else:
                color = color_5mM  # Default to dark blue/purple
            
            # Format label: "Exp-0001: dwater", "Exp-0001: dwater+cycloh", etc.
            filename_clean = base_filename.replace('experiment-T₂ measurement-', '')
            if '_' in filename_clean:
                parts = filename_clean.split('_')
                if len(parts) >= 2:
                    exp_num = parts[0].split('-')[-1] if '-' in parts[0] else parts[0]
                    sample_desc = parts[1].replace('_', ' ')
                    label_text = f"Exp-{exp_num}: {sample_desc}"
                else:
                    label_text = filename_clean.replace('_', ' ')
            else:
                label_text = filename_clean.replace('_', ' ')
            
            # All samples use solid lines
            linestyle = '-'
            
            return color, linestyle, label_text
        
        # Extract concentration and get base color (same for all samples with same concentration)
        # For datasets without concentration (oil/water, cycloh), use sample type instead
        sample_types = []
        colors_list = []
        labels_list = []
        linestyles_list = []
        
        for result in final_results:
            if dataset_number == 1:
                # Use specific color and style mapping for dataset 1
                color, linestyle, label_text = get_dataset1_color_and_style(result['filename'], result['label'])
                colors_list.append(color)
                linestyles_list.append(linestyle)
                labels_list.append(label_text)
            elif dataset_number == 2:
                # Use specific color and style mapping for dataset 2
                color, linestyle, label_text = get_dataset2_color_and_style(result['filename'], result['label'])
                colors_list.append(color)
                linestyles_list.append(linestyle)
                labels_list.append(label_text)
            elif dataset_number == 3:
                # Use specific color and style mapping for dataset 3
                color, linestyle, label_text = get_dataset3_color_and_style(result['filename'], result['label'])
                colors_list.append(color)
                linestyles_list.append(linestyle)
                labels_list.append(label_text)
            elif dataset_number == 4:
                # Use specific color and style mapping for dataset 4
                color, linestyle, label_text = get_dataset4_color_and_style(result['filename'], result['label'])
                colors_list.append(color)
                linestyles_list.append(linestyle)
                labels_list.append(label_text)
            else:
                # Use default logic for unknown datasets
                conc = extract_concentration(result['label'])
                sample_type = extract_sample_type(result['label'], result['filename'])
                
                if conc is not None:
                    # Has concentration - use concentration-based coloring
                    base_color = get_concentration_color(conc)
                    is_T_variant = '(T)' in result['label'] or '_T' in result['label']
                    variant_text = " (T)" if is_T_variant else ""
                    label_text = f"{conc} mM{variant_text}"
                    linestyle = ':' if is_T_variant else '-'
                else:
                    # No concentration - use sample type-based coloring
                    base_color = get_sample_type_color(sample_type)
                    # Create descriptive label from filename
                    filename_clean = result['filename'].replace('experiment-T₂ measurement-', '').replace('.nmrdata', '')
                    # Extract meaningful parts: experiment number and sample type
                    if ' - ' in filename_clean:
                        parts = filename_clean.split(' - ')
                        if len(parts) >= 2:
                            exp_num = parts[0].split('-')[-1] if '-' in parts[0] else parts[0]
                            sample_desc = parts[1].replace('_', ' ')
                            label_text = f"Exp {exp_num}: {sample_desc}"
                        else:
                            label_text = filename_clean
                    else:
                        label_text = filename_clean.replace('_', ' ')
                    linestyle = '-'
                
                sample_types.append(sample_type)
                colors_list.append(base_color)
                linestyles_list.append(linestyle)
                labels_list.append(label_text)
        
        # Plot distributions with appropriate colors and labels
        # Store handles and labels to preserve order in legend
        legend_handles = []
        legend_labels = []
        
        for i, result in enumerate(final_results):
            t2_values = tau
            intensity = result['f']
            base_color = colors_list[i]
            label_text = labels_list[i]
            linestyle = linestyles_list[i]
            
            # Add vertical offset
            offset = i * max_intensity * offset_factor
            
            # Plot the distribution and store handle for legend
            line = ax.semilogx(t2_values, intensity + offset, 
                       linewidth=2, alpha=0.9, color=base_color, linestyle=linestyle,
                       label=label_text)
            legend_handles.append(line[0])
            legend_labels.append(label_text)
            
            # Add label at the far right of the plot (Xigo data uses name)
            tau_max = tau[-1]
            ax.text(tau_max, offset, f"  {label_text}", 
                   fontsize=16, ha='left', va='center', alpha=0.8, fontweight='bold')
        
        # Set title for Xigo data (no time information)
        # Determine dataset name from first result's directory
        if len(final_results) > 0:
            result_dir = final_results[0].get('fd', '')
            if result_dir:
                dataset_name = os.path.basename(os.path.normpath(result_dir.rstrip('/\\')))
            else:
                dataset_name = "Xigo"
        else:
            dataset_name = "Xigo"
        ax.set_title(
            f'Stacked T₂ Distributions - {dataset_name} (λ = {global_optimal_lambda:.2e}, Method = {ilt_method.upper()})\n'
            f'{len(final_results)} samples',
            fontsize=18,
            fontweight='bold'
        )
    else:
        # TNMR data: use time-based colors and labels
        colors = plt.cm.viridis(np.linspace(0, 1, len(final_results)))
        
        for i, (result, color) in enumerate(zip(final_results, colors)):
            # Get the T2 distribution data
            t2_values = tau
            intensity = result['f']
            
            # Add vertical offset
            offset = i * max_intensity * offset_factor
            
            # Plot the distribution with thicker line for better visibility
            ax.semilogx(t2_values, intensity + offset, 
                       linewidth=2, alpha=0.9, color=color,
                       label=f"{result['label']} ({result['time_minutes']:.0f} min)")
            
            # Add time label at the far right of the plot (in hours)
            # Get time in hours for label
            if 'time_minutes' in result:
                time_hours = result['time_minutes'] / 60.0
                time_label = f"{time_hours:.1f} hrs"
            elif 'time_seconds' in result:
                time_hours = result['time_seconds'] / 3600.0
                time_label = f"{time_hours:.1f} hrs"
            else:
                # Fallback: use index-based time
                time_hours = i * 412 / 3600.0  # 412 seconds per experiment
                time_label = f"{time_hours:.1f} hrs"
            
            # Position label at maximum T2 value (tau[-1]) and baseline (offset)
            tau_max = tau[-1]
            ax.text(tau_max, offset, f"  {time_label}", 
                   fontsize=16, ha='left', va='center', alpha=0.8, fontweight='bold')
        
        # Set title for TNMR data (with time information)
        # Calculate times in hours for consistency with axis labels
        start_time_min = final_results[0]['time_minutes']
        end_time_min = final_results[-1]['time_minutes']
        start_hours = start_time_min / 60.0
        end_hours = end_time_min / 60.0
        duration_hours = (end_time_min - start_time_min) / 60.0
        
        if hasattr(args, 'mode') and args.mode != 'xigo':
            selection_summary = f"{len(final_results)} samples (mode: {args.mode}, step={step_size})"
            file_span_summary = f"Files #{processed_file_numbers[0]} to #{processed_file_numbers[-1]}"
        else:
            selection_summary = f"{len(final_results)} samples"
            file_span_summary = ""
        
        ax.set_title(
            f'Stacked T₂ Distributions over Time (λ = {global_optimal_lambda:.2e}, Method = {ilt_method.upper()})\n'
            f'{selection_summary}; {file_span_summary}\n'
            f'Time range: {start_hours:.1f} - {end_hours:.1f} hrs (Duration: {duration_hours:.1f} hrs)',
            fontsize=18,
            fontweight='bold'
        )
    
    # Set labels
    ax.set_xlabel('T₂ Relaxation Time (ms)', fontsize=16)
    ax.set_ylabel('Intensity (a.u.) - Offset for clarity', fontsize=16)
    # Extend xlim to accommodate right-side labels (labels placed at tau[-1])
    # Increased extension factors to prevent text overlap with plot box
    # For Xigo data: extend significantly more to accommodate long filenames
    # For TNMR data: increase extension to accommodate time labels
    if is_xigo_data:
        tau_max_plot = tau[-1] * 20  # Extended further for Xigo data (long filenames)
    else:
        tau_max_plot = tau[-1] * 3.5  # Increased extension for TNMR data to accommodate time labels
    ax.set_xlim([1, tau_max_plot])
    
    # Legend removed - text labels are already placed on the right side of the plot
    # No legend needed since labels are directly on the plot
    
    # Increase tick label sizes for better readability in double-column format
    ax.tick_params(axis='both', which='major', labelsize=14)
    ax.tick_params(axis='both', which='minor', labelsize=12)
    
    ax.grid(True, which='both', alpha=0.3)
    
    plt.tight_layout()
    
    stacked_save_loc = os.path.join(plots_dir, "2D_stacked_T2_distributions.jpg")
    plt.savefig(stacked_save_loc, dpi=300, bbox_inches="tight")
    print(f"2D stacked plot saved: {stacked_save_loc}")
    plt.close()  # Close without showing
    
    # Step 6.5: Generate ITAMeD vs RMEA1D comparison plot (only if ITAMeD was used)
    if ilt_method.lower() == 'itamed':
        print("\n" + "="*80)
        print("STEP 6.5: GENERATING ITAMeD vs RMEA1D COMPARISON PLOT")
        print("="*80)
        
        # For fair comparison, optimize lambda separately for RMEA1D using the reference dataset
        print("Optimizing lambda for RMEA1D (for fair comparison)...")
        # Use the same reference dataset that was used for ITAMeD lambda optimization
        reference_data_for_rmea = final_results[reference_index] if reference_index < len(final_results) else final_results[len(final_results) // 2]
        
        # Use RMEA1D lambda optimization
        lambda_values_rmea = np.logspace(-4, 2, 50)  # RMEA range
        res_norms_rmea, sol_norms_rmea, _ = compute_lcurve_rmea(
            reference_data_for_rmea['time_echoes'], 
            reference_data_for_rmea['peak_int_raw'], 
            tau, 
            lambda_values_rmea,
            method='rmea1d'
        )
        optimal_idx_rmea = choose_lambda_balanced(lambda_values_rmea, res_norms_rmea, sol_norms_rmea)
        lambda_selected_rmea = lambda_values_rmea[optimal_idx_rmea]
        optimal_lambda_rmea = lambda_selected_rmea / 3.0  # Apply RMEA adjustment (λ/3)
        print(f"  RMEA1D optimal lambda: {optimal_lambda_rmea:.2e} (from grid: {lambda_selected_rmea:.2e})")
        print(f"  ITAMeD optimal lambda: {global_optimal_lambda:.2e}")
        
        # Select a few representative datasets for comparison (first, middle, last)
        num_comparison_samples = min(5, len(final_results))
        if len(final_results) <= 5:
            comparison_indices = list(range(len(final_results)))
        else:
            comparison_indices = [
                0,  # First
                len(final_results) // 4,  # 25%
                len(final_results) // 2,  # Middle
                3 * len(final_results) // 4,  # 75%
                len(final_results) - 1  # Last
            ]
        
        print(f"Generating comparison plot for {len(comparison_indices)} representative samples...")
        print(f"  Using ITAMeD lambda: {global_optimal_lambda:.2e}")
        print(f"  Using RMEA1D lambda: {optimal_lambda_rmea:.2e}")
        
        # Create comparison figure with subplots
        fig, axes = plt.subplots(len(comparison_indices), 2, figsize=(16, 5*len(comparison_indices)))
        if len(comparison_indices) == 1:
            axes = axes.reshape(1, -1)
        
        for row_idx, data_idx in enumerate(comparison_indices):
            result = final_results[data_idx]
            
            # Compute RMEA1D result for comparison using RMEA1D's optimal lambda
            print(f"  Computing RMEA1D for comparison: {result['label']}...")
            f_rmea, mc_rmea = rmea1d(result['time_echoes'], result['peak_int_raw'], tau, optimal_lambda_rmea)
            
            # Get ITAMeD result (already computed)
            f_itamed = result['f']
            mc_itamed = result['mc']
            
            # Calculate differences (absolute and relative)
            f_diff = np.abs(f_itamed - f_rmea)
            mc_diff = np.abs(mc_itamed - mc_rmea)
            max_f_diff = np.max(f_diff)
            max_mc_diff = np.max(mc_diff)
            
            # Calculate relative differences (as fraction of signal intensity)
            signal_intensity = result['signal_intensity']
            max_f_rel_diff = max_f_diff / signal_intensity if signal_intensity > 0 else 0
            max_mc_rel_diff = max_mc_diff / signal_intensity if signal_intensity > 0 else 0
            
            # Store for summary analysis
            result['comparison_max_f_diff'] = max_f_diff
            result['comparison_max_mc_diff'] = max_mc_diff
            result['comparison_max_f_rel_diff'] = max_f_rel_diff
            result['comparison_max_mc_rel_diff'] = max_mc_rel_diff
            
            # Left plot: T2 distributions comparison
            ax_left = axes[row_idx, 0]
            ax_left.semilogx(tau, f_itamed, 'b-', linewidth=2.5, 
                           label=f'ITAMeD L2 (λ={global_optimal_lambda:.2e})', alpha=0.8)
            ax_left.semilogx(tau, f_rmea, 'r--', linewidth=2.5, 
                           label=f'RMEA1D (λ={optimal_lambda_rmea:.2e})', alpha=0.8)
            ax_left.semilogx(tau, f_diff, 'g:', linewidth=1.5, label=f'Difference (max={max_f_diff:.2e})', alpha=0.6)
            ax_left.set_xlabel('T₂ Relaxation Time (ms)', fontsize=11)
            ax_left.set_ylabel('Amplitude', fontsize=11)
            ax_left.set_title(f"{result['label']} - T2 Distribution Comparison", fontweight='bold', fontsize=12)
            ax_left.set_xlim([1, 100000])
            ax_left.legend(fontsize=9, loc='best')
            ax_left.grid(True, which='both', alpha=0.3)
            
            # Add text box with difference statistics (absolute and relative)
            textstr = (f'Abs diff: {max_f_diff:.2e}\n'
                      f'Mean abs: {np.mean(f_diff):.2e}\n'
                      f'Rel diff: {max_f_rel_diff:.2e}\n'
                      f'Signal: {signal_intensity:.6f}')
            props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
            ax_left.text(0.02, 0.98, textstr, transform=ax_left.transAxes, fontsize=9,
                        verticalalignment='top', bbox=props)
            
            # Right plot: Time-domain fit comparison
            ax_right = axes[row_idx, 1]
            ax_right.plot(result['time_echoes'], result['peak_int_raw'], 'ko', markersize=3, 
                         label='Exp. data', alpha=0.6)
            ax_right.plot(result['time_echoes'], mc_itamed, 'b-', linewidth=2.5, 
                         label=f'ITAMeD L2 fit (λ={global_optimal_lambda:.2e})', alpha=0.8)
            ax_right.plot(result['time_echoes'], mc_rmea, 'r--', linewidth=2.5, 
                         label=f'RMEA1D fit (λ={optimal_lambda_rmea:.2e})', alpha=0.8)
            ax_right.plot(result['time_echoes'], mc_diff, 'g:', linewidth=1.5, 
                         label=f'Difference (max={max_mc_diff:.2e})', alpha=0.6)
            ax_right.set_xlabel('Time (ms)', fontsize=11)
            ax_right.set_ylabel('Amplitude', fontsize=11)
            ax_right.set_title(f"{result['label']} - Time-Domain Fit Comparison", fontweight='bold', fontsize=12)
            if len(result['time_echoes']) > 0:
                ax_right.set_xlim([0, result['time_echoes'][-1] * 1.05])
            ax_right.legend(fontsize=9, loc='best')
            ax_right.grid(True, alpha=0.3)
            
            # Add text box with difference statistics (absolute and relative)
            textstr = (f'Abs diff: {max_mc_diff:.2e}\n'
                      f'Mean abs: {np.mean(mc_diff):.2e}\n'
                      f'Rel diff: {max_mc_rel_diff:.2e}\n'
                      f'Signal: {signal_intensity:.6f}')
            ax_right.text(0.02, 0.98, textstr, transform=ax_right.transAxes, fontsize=9,
                         verticalalignment='top', bbox=props)
        
        fig.suptitle(
            f'ITAMeD L2 vs RMEA1D Comparison\n'
            f'ITAMeD λ = {global_optimal_lambda:.2e} | RMEA1D λ = {optimal_lambda_rmea:.2e}\n'
            f'Showing {len(comparison_indices)} representative samples',
            fontsize=14, fontweight='bold', y=0.995
        )
        plt.tight_layout(rect=[0, 0, 1, 0.99])
        
        comparison_save_loc = os.path.join(plots_dir, "ITAMeD_vs_RMEA1D_comparison.jpg")
        plt.savefig(comparison_save_loc, dpi=300, bbox_inches="tight")
        print(f"ITAMeD vs RMEA1D comparison plot saved: {comparison_save_loc}")
        plt.close()
        
        # Generate summary plot: Differences vs Signal Intensity
        print("Generating difference vs signal intensity summary plot...")
        comparison_results = [final_results[idx] for idx in comparison_indices]
        signal_intensities = [r['signal_intensity'] for r in comparison_results]
        max_f_diffs = [r.get('comparison_max_f_diff', 0) for r in comparison_results]
        max_mc_diffs = [r.get('comparison_max_mc_diff', 0) for r in comparison_results]
        max_f_rel_diffs = [r.get('comparison_max_f_rel_diff', 0) for r in comparison_results]
        max_mc_rel_diffs = [r.get('comparison_max_mc_rel_diff', 0) for r in comparison_results]
        
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        
        # Top left: Absolute distribution difference vs signal intensity
        ax1 = axes[0, 0]
        ax1.plot(signal_intensities, max_f_diffs, 'bo-', linewidth=2, markersize=8, label='Max |f_ITAMeD - f_RMEA|')
        ax1.set_xlabel('Signal Intensity (raw)', fontsize=11)
        ax1.set_ylabel('Absolute Difference', fontsize=11)
        ax1.set_title('Distribution Difference (Absolute) vs Signal Intensity', fontweight='bold', fontsize=12)
        ax1.legend(fontsize=10)
        ax1.grid(True, alpha=0.3)
        
        # Top right: Relative distribution difference vs signal intensity
        ax2 = axes[0, 1]
        ax2.plot(signal_intensities, max_f_rel_diffs, 'ro-', linewidth=2, markersize=8, label='Max |f_ITAMeD - f_RMEA| / Signal')
        ax2.set_xlabel('Signal Intensity (raw)', fontsize=11)
        ax2.set_ylabel('Relative Difference', fontsize=11)
        ax2.set_title('Distribution Difference (Relative) vs Signal Intensity', fontweight='bold', fontsize=12)
        ax2.legend(fontsize=10)
        ax2.grid(True, alpha=0.3)
        
        # Bottom left: Absolute fit difference vs signal intensity
        ax3 = axes[1, 0]
        ax3.plot(signal_intensities, max_mc_diffs, 'go-', linewidth=2, markersize=8, label='Max |mc_ITAMeD - mc_RMEA|')
        ax3.set_xlabel('Signal Intensity (raw)', fontsize=11)
        ax3.set_ylabel('Absolute Difference', fontsize=11)
        ax3.set_title('Fit Difference (Absolute) vs Signal Intensity', fontweight='bold', fontsize=12)
        ax3.legend(fontsize=10)
        ax3.grid(True, alpha=0.3)
        
        # Bottom right: Relative fit difference vs signal intensity
        ax4 = axes[1, 1]
        ax4.plot(signal_intensities, max_mc_rel_diffs, 'mo-', linewidth=2, markersize=8, label='Max |mc_ITAMeD - mc_RMEA| / Signal')
        ax4.set_xlabel('Signal Intensity (raw)', fontsize=11)
        ax4.set_ylabel('Relative Difference', fontsize=11)
        ax4.set_title('Fit Difference (Relative) vs Signal Intensity', fontweight='bold', fontsize=12)
        ax4.legend(fontsize=10)
        ax4.grid(True, alpha=0.3)
        
        fig.suptitle(
            f'ITAMeD vs RMEA1D: Difference Scaling with Signal Intensity\n'
            f'ITAMeD λ = {global_optimal_lambda:.2e} | RMEA1D λ = {optimal_lambda_rmea:.2e}',
            fontsize=14, fontweight='bold', y=0.995
        )
        plt.tight_layout(rect=[0, 0, 1, 0.99])
        
        scaling_save_loc = os.path.join(plots_dir, "ITAMeD_vs_RMEA1D_difference_scaling.jpg")
        plt.savefig(scaling_save_loc, dpi=300, bbox_inches="tight")
        print(f"Difference scaling plot saved: {scaling_save_loc}")
        plt.close()
        
        # Print summary statistics
        print("\n" + "="*80)
        print("DIFFERENCE SCALING ANALYSIS")
        print("="*80)
        print(f"Signal intensity range: {min(signal_intensities):.6f} to {max(signal_intensities):.6f}")
        print(f"Absolute distribution difference range: {min(max_f_diffs):.6e} to {max(max_f_diffs):.6e}")
        print(f"Relative distribution difference range: {min(max_f_rel_diffs):.6e} to {max(max_f_rel_diffs):.6e}")
        print(f"Absolute fit difference range: {min(max_mc_diffs):.6e} to {max(max_mc_diffs):.6e}")
        print(f"Relative fit difference range: {min(max_mc_rel_diffs):.6e} to {max(max_mc_rel_diffs):.6e}")
        
        # Check if differences scale linearly with signal
        if len(signal_intensities) > 1:
            # Calculate correlation between signal intensity and absolute differences
            corr_f_abs = np.corrcoef(signal_intensities, max_f_diffs)[0, 1]
            corr_mc_abs = np.corrcoef(signal_intensities, max_mc_diffs)[0, 1]
            corr_f_rel = np.corrcoef(signal_intensities, max_f_rel_diffs)[0, 1]
            corr_mc_rel = np.corrcoef(signal_intensities, max_mc_rel_diffs)[0, 1]
            
            print(f"\nCorrelation coefficients:")
            print(f"  Signal vs Absolute dist diff: {corr_f_abs:.3f}")
            print(f"  Signal vs Relative dist diff: {corr_f_rel:.3f}")
            print(f"  Signal vs Absolute fit diff: {corr_mc_abs:.3f}")
            print(f"  Signal vs Relative fit diff: {corr_mc_rel:.3f}")
            
            if corr_f_abs > 0.7:
                print(f"\n[CONCLUSION] Absolute differences INCREASE with signal intensity (strong positive correlation)")
            elif corr_f_abs < -0.7:
                print(f"\n[CONCLUSION] Absolute differences DECREASE with signal intensity (strong negative correlation)")
            else:
                print(f"\n[CONCLUSION] Absolute differences show WEAK correlation with signal intensity")
            
            if abs(corr_f_rel) < 0.3:
                print(f"[CONCLUSION] Relative differences are RELATIVELY CONSTANT (weak correlation)")
                print(f"            This suggests differences scale proportionally with signal intensity")
            elif corr_f_rel > 0.3:
                print(f"[CONCLUSION] Relative differences INCREASE with signal intensity")
            else:
                print(f"[CONCLUSION] Relative differences DECREASE with signal intensity")
    
    # Step 7: Generate combined lambda variation plot for all datasets (optional)
    if generate_lambda_variation:
        print("\n" + "="*80)
        print("STEP 7: GENERATING LAMBDA VARIATION SUMMARY PLOT")
        print("="*80)
        
        # Calculate lambda values
        lambda_optimal = global_optimal_lambda
        lambda_mul_1_25 = lambda_optimal * 1.25
        lambda_mul_1_5 = lambda_optimal * 1.5
        lambda_mul_2 = lambda_optimal * 2
        lambda_div_1_25 = lambda_optimal / 1.25
        
        print(f"Generating lambda variation plots: {num_datasets} samples split across {num_pages} page(s)...")
        
        for page_num in range(num_pages):
            start_idx = page_num * max_rows_per_page
            end_idx = min(start_idx + max_rows_per_page, num_datasets)
            rows_this_page = end_idx - start_idx
            
            print(f"  Creating lambda variation page {page_num + 1}/{num_pages} (samples {start_idx + 1}-{end_idx})...")
            
            # Create combined figure with all datasets as subplots
            fig, axes = plt.subplots(rows_this_page, 2, figsize=(16, 6*rows_this_page))
            
            # Ensure axes is 2D (even for single dataset)
            if rows_this_page == 1:
                axes = axes.reshape(1, -1)
            
            for local_row_idx, global_idx in enumerate(range(start_idx, end_idx)):
                result = final_results[global_idx]
                color = colors[global_idx]
                row_idx = local_row_idx
                
                print(f"    Calculating lambda variations for {result['label']}...")
                
                # Use raw peak integrals (no normalization)
                f_optimal, mc_optimal = perform_ilt(result['time_echoes'], result['peak_int_raw'], tau, lambda_optimal, method=ilt_method)
                f_mul_1_25, mc_mul_1_25 = perform_ilt(result['time_echoes'], result['peak_int_raw'], tau, lambda_mul_1_25, method=ilt_method)
                f_mul_1_5, mc_mul_1_5 = perform_ilt(result['time_echoes'], result['peak_int_raw'], tau, lambda_mul_1_5, method=ilt_method)
                f_mul_2, mc_mul_2 = perform_ilt(result['time_echoes'], result['peak_int_raw'], tau, lambda_mul_2, method=ilt_method)
                f_div_1_25, mc_div_1_25 = perform_ilt(result['time_echoes'], result['peak_int_raw'], tau, lambda_div_1_25, method=ilt_method)
                
                # Plot T2 distributions
                axes[row_idx, 0].semilogx(tau, f_optimal, linewidth=2.5, color=color, 
                                          label=f'Optimal λ = {lambda_optimal:.2e}', alpha=0.9)
                axes[row_idx, 0].semilogx(tau, f_mul_1_25, linewidth=2, color=color, 
                                          label=f'λ×1.25 = {lambda_mul_1_25:.2e}', alpha=0.7, linestyle='--')
                axes[row_idx, 0].semilogx(tau, f_mul_1_5, linewidth=2, color=color, 
                                          label=f'λ×1.5 = {lambda_mul_1_5:.2e}', alpha=0.6, linestyle='-.')
                axes[row_idx, 0].semilogx(tau, f_mul_2, linewidth=2, color=color, 
                                          label=f'λ×2 = {lambda_mul_2:.2e}', alpha=0.5, linestyle=':')
                axes[row_idx, 0].semilogx(tau, f_div_1_25, linewidth=2, color=color, 
                                          label=f'λ/1.25 = {lambda_div_1_25:.2e}', alpha=0.8, linestyle='-')
                axes[row_idx, 0].set_xlabel('T2 Relaxation Time (ms)', fontsize=11)
                axes[row_idx, 0].set_ylabel('Amplitude', fontsize=11)
                axes[row_idx, 0].set_title(f'{result["label"]} - Effect of λ on T2 Distribution', fontweight='bold')
                axes[row_idx, 0].set_xlim([1, 100000])
                axes[row_idx, 0].legend(fontsize=8)
                axes[row_idx, 0].grid(True, which='both', alpha=0.3)
                
                # Plot fits - use raw peak integrals (no scaling needed since ILT uses raw input)
                peak_int_raw = result['peak_int_raw']
                
                axes[row_idx, 1].plot(result['time_echoes'], peak_int_raw, 'ko', markersize=4, 
                                     label='Exp. data', alpha=0.7)
                axes[row_idx, 1].plot(result['time_echoes'], mc_optimal, linewidth=2.5, color=color,
                                     label=f'Optimal λ = {lambda_optimal:.2e}', alpha=0.9)
                axes[row_idx, 1].plot(result['time_echoes'], mc_mul_1_25, linewidth=2, color=color,
                                     label=f'λ×1.25 = {lambda_mul_1_25:.2e}', alpha=0.7, linestyle='--')
                axes[row_idx, 1].plot(result['time_echoes'], mc_mul_1_5, linewidth=2, color=color,
                                     label=f'λ×1.5 = {lambda_mul_1_5:.2e}', alpha=0.6, linestyle='-.')
                axes[row_idx, 1].plot(result['time_echoes'], mc_mul_2, linewidth=2, color=color,
                                     label=f'λ×2 = {lambda_mul_2:.2e}', alpha=0.5, linestyle=':')
                axes[row_idx, 1].plot(result['time_echoes'], mc_div_1_25, linewidth=2, color=color,
                                     label=f'λ/1.25 = {lambda_div_1_25:.2e}', alpha=0.8, linestyle='-')
                axes[row_idx, 1].set_xlabel('Time (ms)', fontsize=11)
                axes[row_idx, 1].set_ylabel('Amplitude', fontsize=11)
                # Ensure full decay is shown
                if len(result['time_echoes']) > 0:
                    axes[row_idx, 1].set_xlim([0, result['time_echoes'][-1] * 1.05])
                axes[row_idx, 1].set_title(f'{result["label"]} - Effect of λ on Fit Quality', fontweight='bold')
                axes[row_idx, 1].legend(fontsize=8)
                axes[row_idx, 1].grid(True, alpha=0.3)
            
            page_suffix = f"_page{page_num + 1}" if num_pages > 1 else ""
            fig.suptitle(f'Lambda Variation Analysis: Samples {start_idx + 1}-{end_idx}', 
                         fontsize=16, fontweight='bold', y=0.995)
            plt.tight_layout(rect=[0, 0, 1, 0.99])
            
            # Save combined lambda variation figure (don't display)
            lambda_summary_save_loc = os.path.join(plots_dir, f"summary_lambda_variation{page_suffix}.jpg")
            plt.savefig(lambda_summary_save_loc, dpi=300, bbox_inches="tight")
            print(f"  Lambda variation page {page_num + 1} saved: {lambda_summary_save_loc}")
            plt.close(fig)  # Close without showing
    else:
        print("\n" + "="*80)
        print("STEP 7: SKIPPING LAMBDA VARIATION PLOTS")
        print("="*80)
        print("Lambda variation plots are disabled. Skipping Step 7.")
    
    # Step 8: Analyze peak integrals (Short T2 and Long T2 components)
    print("\n" + "="*80)
    print("STEP 8: ANALYZING PEAK INTEGRALS")
    print("="*80)
    
    # Get tau from reference data (same tau used for all analyses)
    tau_for_analysis = reference_data['tau']
    
    # Call peak area analysis function
    peak_area_results = analyze_peak_integrals(final_results, tau_for_analysis, save_dir=plots_dir)
    
    # Store peak area results in final_results for potential future use
    for idx, result in enumerate(final_results):
        result['short_t2_area'] = peak_area_results['short_t2_areas'][idx]
        result['long_t2_area'] = peak_area_results['long_t2_areas'][idx]
        result['valley_index'] = peak_area_results['valley_indices'][idx]
        result['peak1_index'] = peak_area_results['peak1_indices'][idx]
        result['peak2_index'] = peak_area_results['peak2_indices'][idx]
    
    # Step 8.5: Generate integration verification plot
    # Call integration verification plot function
    plot_integration_verification(final_results, tau_for_analysis, peak_area_results, save_dir=plots_dir)
    
    print("\n" + "="*80)
    print("ALL ANALYSES COMPLETE!")
    print("="*80)
    print(f"\nSummary:")
    if hasattr(args, 'mode') and args.mode != 'xigo':
        print(f"- {len(final_results)} datasets processed (mode: {args.mode}, step={step_size})")
        print(f"- File range: #{processed_file_numbers[0]} to #{processed_file_numbers[-1]}")
        print(f"- File numbers processed: {describe_file_selection(processed_file_numbers)}")
    else:
        print(f"- {len(final_results)} datasets processed (Xigo data)")
        print(f"- Files processed: {', '.join([r['label'] for r in final_results])}")
    
    # Echo count statistics
    echo_counts = [len(r['time_echoes']) for r in final_results]
    print(f"- Echo counts: min={min(echo_counts)}, max={max(echo_counts)}, mean={np.mean(echo_counts):.1f}")
    
    experiment_interval_seconds = 412
    analyzed_interval_seconds = experiment_interval_seconds * step_size
    print(f"- Time per experiment: {experiment_interval_seconds} seconds ({experiment_interval_seconds / 60:.2f} minutes)")
    print(f"- Time between analyzed samples: {analyzed_interval_seconds} seconds ({analyzed_interval_seconds / 60:.2f} minutes)")
    print(f"- Experiment start time: {final_results[0]['time_minutes']:.1f} minutes ({final_results[0]['time_minutes']/60:.1f} hours)")
    print(f"- Experiment end time: {final_results[-1]['time_minutes']:.1f} minutes ({final_results[-1]['time_minutes']/60:.1f} hours)")
    print(f"- Duration analyzed: {(final_results[-1]['time_minutes'] - final_results[0]['time_minutes']):.1f} minutes ({(final_results[-1]['time_minutes'] - final_results[0]['time_minutes'])/60:.1f} hours)")
    print(f"- Global optimal lambda: lambda = {global_optimal_lambda:.2e}")
    
    # Try to extract reference file number (for TNMR data)
    try:
        if reference_data['label'].startswith('Sample_') and '_' in reference_data['label']:
            reference_display_number = int(reference_data['label'].split('_')[1])
            print(f"- Reference dataset: {reference_data['filename']} (File #{reference_display_number}, {len(reference_data['time_echoes'])} data points)")
        else:
            print(f"- Reference dataset: {reference_data['filename']} ({reference_data['label']}, {len(reference_data['time_echoes'])} data points)")
    except (ValueError, IndexError):
        print(f"- Reference dataset: {reference_data['filename']} ({reference_data['label']}, {len(reference_data['time_echoes'])} data points)")
    
    print(f"- All figures saved to: {plots_dir}")
    # Get base_dir from results if not available
    if 'base_dir' not in locals() or base_dir is None:
        if len(final_results) > 0:
            base_dir = final_results[0].get('fd', os.getcwd())
        else:
            base_dir = os.getcwd()
    print(f"- Experimental details saved to: {base_dir}")

