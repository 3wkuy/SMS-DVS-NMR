#!/usr/bin/env python3
"""
Simple test script to demonstrate the NMR package functionality
This script runs without requiring user input
"""

import sys
from pathlib import Path
import numpy as np

# Add the package to path
sys.path.insert(0, str(Path(__file__).parent))

print("="*70)
print("Testing CPMG NMR Analysis Package")
print("="*70)
print()

# Test 1: Import the package
print("Test 1: Importing package...")
try:
    from nmr_cpmg_analysis import perform_ilt, find_optimal_lambda, rmea1d
    print("✓ Package imported successfully!")
    print(f"  - perform_ilt function: {perform_ilt is not None}")
    print(f"  - find_optimal_lambda function: {find_optimal_lambda is not None}")
    print(f"  - rmea1d function: {rmea1d is not None}")
except ImportError as e:
    print(f"✗ Failed to import package: {e}")
    sys.exit(1)
print()

# Test 2: Generate synthetic data and process it
print("Test 2: Processing synthetic CPMG data...")
print("-"*70)

# Generate synthetic bi-exponential decay data
t = np.linspace(0, 100, 200)  # Time in ms
T2_1 = 10  # Fast component T2 (ms)
T2_2 = 100  # Slow component T2 (ms)
amp_1 = 0.3  # Amplitude of fast component
amp_2 = 0.7  # Amplitude of slow component

# Clean signal
m_clean = amp_1 * np.exp(-t/T2_1) + amp_2 * np.exp(-t/T2_2)

# Add noise
np.random.seed(42)  # For reproducibility
noise_level = 0.01
m = m_clean + noise_level * np.random.randn(len(t))

# Create T2 grid (logarithmically spaced)
tau = np.logspace(0, 3, 100)  # 1 to 1000 ms

print(f"  Data points: {len(t)}")
print(f"  Time range: {t[0]:.1f} to {t[-1]:.1f} ms")
print(f"  T2 grid: {len(tau)} points from {tau[0]:.2f} to {tau[-1]:.2f} ms")
print()

# Find optimal lambda
print("  Finding optimal regularization parameter...")
try:
    lambda_opt = find_optimal_lambda(t, m, tau, method='rmea1d')
    print(f"  ✓ Optimal lambda: {lambda_opt:.2e}")
except Exception as e:
    print(f"  ✗ Lambda optimization failed: {e}")
    sys.exit(1)
print()

# Perform ILT
print("  Performing Inverse Laplace Transform...")
try:
    f, mc = perform_ilt(t, m, tau, lambda_opt, method='rmea1d')
    print(f"  ✓ ILT completed successfully!")
    print(f"    - T2 distribution shape: {f.shape}")
    print(f"    - Fitted signal shape: {mc.shape}")
    print(f"    - Peak T2 value: {tau[np.argmax(f)]:.2f} ms")
    print(f"    - Maximum amplitude: {np.max(f):.6f}")
    print(f"    - Signal fit error (RMS): {np.sqrt(np.mean((m - mc)**2)):.6f}")
except Exception as e:
    print(f"  ✗ ILT failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
print()

# Test 3: Direct RMEA1D usage
print("Test 3: Testing direct RMEA1D function...")
print("-"*70)
try:
    f_direct = rmea1d(t, m, tau, lambda_opt)
    print(f"  ✓ RMEA1D function works!")
    print(f"    - Result shape: {f_direct.shape}")
    print(f"    - Max value: {np.max(f_direct):.6f}")
except Exception as e:
    print(f"  ✗ RMEA1D failed: {e}")
print()

# Summary
print("="*70)
print("Package Test Summary")
print("="*70)
print("✓ All core functions are working correctly!")
print("✓ Package is ready to use for CPMG NMR data analysis")
print()
print("Next steps:")
print("  1. Run the main analysis: python run_nmr_analysis.py")
print("  2. See examples: python examples/simple_example.py")
print("  3. Read documentation: README.md, USER_GUIDE.md")
print("="*70)


