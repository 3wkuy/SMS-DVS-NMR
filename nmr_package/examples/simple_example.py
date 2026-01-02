#!/usr/bin/env python3
"""
Simple example of using the CPMG NMR Analysis package
This demonstrates basic usage for a single file
"""

import sys
from pathlib import Path
import numpy as np

# Add the package to path (if not installed)
sys.path.insert(0, str(Path(__file__).parent.parent))

from nmr_cpmg_analysis import perform_ilt, find_optimal_lambda

# ============================================
# Example 1: Process synthetic data
# ============================================

def example_synthetic_data():
    """Generate and process synthetic CPMG data"""
    print("="*60)
    print("Example 1: Synthetic Data")
    print("="*60)
    print()

    # Generate synthetic data (bi-exponential decay)
    t = np.linspace(0, 100, 200)  # Time in ms
    T2_1 = 10  # Fast component T2 (ms)
    T2_2 = 100  # Slow component T2 (ms)
    amp_1 = 0.3  # Amplitude of fast component
    amp_2 = 0.7  # Amplitude of slow component

    # Clean signal
    m_clean = amp_1 * np.exp(-t/T2_1) + amp_2 * np.exp(-t/T2_2)

    # Add noise
    noise_level = 0.01
    m = m_clean + noise_level * np.random.randn(len(t))

    # Create T2 grid (logarithmically spaced)
    tau = np.logspace(0, 3, 100)  # 1 to 1000 ms

    print(f"Data points: {len(t)}")
    print(f"Time range: {t[0]:.1f} to {t[-1]:.1f} ms")
    print(f"T2 grid: {len(tau)} points from {tau[0]:.2f} to {tau[-1]:.2f} ms")
    print()

    # Find optimal lambda
    print("Finding optimal regularization parameter...")
    lambda_opt = find_optimal_lambda(t, m, tau, method='rmea1d')
    print(f"Optimal lambda: {lambda_opt:.2e}")
    print()

    # Perform ILT
    print("Performing Inverse Laplace Transform...")
    f, mc = perform_ilt(t, m, tau, lambda_opt, method='rmea1d')
    print()

    # Analyze results
    print("="*60)
    print("Results")
    print("="*60)
    print(f"T2 distribution computed")
    print(f"Peak T2 value: {tau[np.argmax(f)]:.2f} ms")
    print(f"Maximum amplitude: {np.max(f):.6f}")
    print(f"Signal fit error (RMS): {np.sqrt(np.mean((m - mc)**2)):.6f}")
    print()

    # Optional: Save results
    # np.savetxt('results.csv', np.column_stack([tau, f]), delimiter=',', header='tau_ms,amplitude', comments='')

    return t, m, tau, f, mc


# ============================================
# Example 2: Process real data from file
# ============================================

def example_from_file(filename):
    """Process CPMG data from a CSV file"""
    print("="*60)
    print("Example 2: Data from File")
    print("="*60)
    print()

    # Load data
    try:
        data = np.loadtxt(filename, delimiter=',', skiprows=1)
        t = data[:, 0]  # Time column
        m = data[:, 1]  # Signal column
    except Exception as e:
        print(f"Error loading file: {e}")
        print("Expected format: CSV with time (col 0) and signal (col 1)")
        return None

    print(f"Loaded data from: {filename}")
    print(f"Data points: {len(t)}")
    print(f"Time range: {t[0]:.2f} to {t[-1]:.2f} ms")
    print()

    # Create T2 grid
    tau_min = np.log10(t[0])
    tau_max = np.log10(t[-1]) + 1
    tau = np.logspace(tau_min, tau_max, 100)

    print(f"T2 grid: {len(tau)} points from {tau[0]:.2f} to {tau[-1]:.2f} ms")
    print()

    # Find optimal lambda
    print("Finding optimal regularization parameter...")
    lambda_opt = find_optimal_lambda(t, m, tau, method='rmea1d')
    print(f"Optimal lambda: {lambda_opt:.2e}")
    print()

    # Perform ILT
    print("Performing Inverse Laplace Transform...")
    f, mc = perform_ilt(t, m, tau, lambda_opt, method='rmea1d')
    print()

    # Analyze results
    print("="*60)
    print("Results")
    print("="*60)
    print(f"T2 distribution computed")
    print(f"Peak T2 value: {tau[np.argmax(f)]:.2f} ms")
    print(f"Maximum amplitude: {np.max(f):.6f}")
    print(f"Signal fit error (RMS): {np.sqrt(np.mean((m - mc)**2)):.6f}")
    print()

    return t, m, tau, f, mc


# ============================================
# Main execution
# ============================================

if __name__ == "__main__":
    print()
    print("CPMG NMR Analysis - Simple Examples")
    print("="*60)
    print()

    # Run synthetic example
    example_synthetic_data()

    print()
    print("-"*60)
    print()

    # Ask user if they want to process a file
    print("Would you like to process a file?")
    response = input("Enter file path (or press Enter to skip): ").strip()

    if response:
        # Process the file
        results = example_from_file(response)
        if results is not None:
            t, m, tau, f, mc = results
            print("Analysis complete!")
    else:
        print("Skipping file processing.")

    print()
    print("="*60)
    print("Examples completed!")
    print("="*60)
    print()
    print("To learn more, see:")
    print("  - README.md: Overview and installation")
    print("  - USER_GUIDE.md: Detailed documentation")
    print("  - run_nmr_analysis.py: Main analysis script")
    print()

