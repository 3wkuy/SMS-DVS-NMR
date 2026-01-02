"""
ITAMeD L2 Version - Inverse Laplace Transform with L2 Regularization

This module provides ITAMeD functions with L2 (smooth) regularization,
which is better suited for broad, smooth peaks compared to L1 (sparse) regularization.

L2 regularization produces smoother distributions and is recommended for
experimental data with broad relaxation time distributions.
"""

import numpy as np
from .core import generate_matrix_1d
from alive_progress import alive_bar


def itamed1d_l2(iter, diffusion_range, signal, b, llambda, expclass, regularization='L2'):
    """
    Function for main processing of 1D Laplace data with L2 regularization.
    
    This is similar to itamed1d but uses L2 regularization instead of L1,
    producing smoother, broader peaks suitable for experimental data.
    
    Inputs:
    -------
    iter : int
        Maximum number of iterations
    diffusion_range : array-like
        Vector of 3 parameters [Minimal Diffusion, Maximum diffusion, number of points]
        In case of T1 and T2 experiments T1 or T2 time respectively
    signal : array-like
        Signal (Diffusion decay, CPMG, T1 saturation or inversion)
    b : array-like
        Vector of b in eq. I = exp(-D * b)
    llambda : float
        Lagrangian multiplier (regularization parameter)
    expclass : str
        Experiment class. Available choices:
        'D' - diffusion experiment,
        'T2'- CPMG,
        'T1' T1 inversion recovery,
        'T1sat', T1 saturation recovery
    regularization : str
        Regularization type ('L2' for smooth peaks, 'L1' for sparse peaks)
        Default: 'L2'
    
    Outputs:
    --------
    d_scale : array
        Vector of Diffusion coefficient of relaxation times
    out_array : array
        Result of ITAMeD ILT with L2 regularization
    """
    signal = np.array(signal)
    b = np.array(b)
    d_scale = np.logspace(np.log10(diffusion_range[0]),
                          np.log10(diffusion_range[1]), 
                          int(diffusion_range[2]))
    a = np.zeros(d_scale.shape)
    mat = generate_matrix_1d(d_scale, b, expclass)
    out_array = fista_l2(a, signal, llambda, mat, iter)
    return d_scale, out_array


def fista_l2(a, signal, lambdal, matal, iterk):
    """
    FISTA algorithm with L2 regularization (smooth peaks).
    
    This uses L2 (Tikhonov) regularization instead of L1 (sparse) regularization.
    L2 regularization minimizes ||Ax - b||^2 + lambda * ||x||^2,
    which produces smoother, broader peaks suitable for experimental data.
    
    Parameters:
    -----------
    a : array
        Initial guess (usually zeros)
    signal : array
        Signal measurements
    lambdal : float
        Regularization parameter
    matal : array
        Kernel matrix
    iterk : int
        Number of iterations
    
    Returns:
    --------
    x : array
        Reconstructed distribution with L2 regularization
    """
    iterk = int(iterk)
    signal = np.matrix(signal).T
    matal = np.matrix(matal)
    
    # Compute step size for L2 regularized problem
    # For L2: minimize ||Ax - b||^2 + lambda * ||x||^2
    # The gradient is: 2*A^T*(A*x - b) + 2*lambda*x
    # Step size based on largest eigenvalue of (A^T*A + lambda*I)
    ATA = np.matmul(matal.T, matal)
    max_eig = np.max(np.real(np.linalg.eig(ATA + lambdal * np.eye(ATA.shape[0]))[0]))
    t = 1 / (2 * max_eig)
    
    a = np.matrix(a)
    y = np.matrix(a.T)
    x = np.matrix(y)
    s = 1
    
    # Precompute: 2*t*A^T for efficiency
    tmatal = 2 * t * matal.T
    # L2 regularization term: 2*t*lambda
    lambda_term = 2 * t * lambdal
    
    with alive_bar(iterk, force_tty=True) as bar:
        for kw in range(iterk):
            # Gradient step with L2 regularization
            # Gradient: A^T*(A*y - signal) + lambda*y
            residual = matal * y - signal
            gradient = tmatal * residual + lambda_term * y
            c = y - gradient
            
            # For L2 regularization, we don't use hard thresholding
            # Instead, we just ensure non-negativity
            x1 = np.maximum(c, 0)
            
            # FISTA acceleration step
            s1 = (1 + np.sqrt((1 + 4 * s ** 2))) / 2
            y = x1 + (s - 1) / s1 * (x1 - x)
            s = s1
            x = np.matrix(x1)
            bar()
    
    return x

