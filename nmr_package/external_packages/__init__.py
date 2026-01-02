"""
External Packages for CPMG NMR Analysis

This module includes third-party packages bundled with the main package.
Currently includes: ITAMeD (Inverse Laplace Transform library)
"""

# Import ITAMeD processing module
try:
    from . import processing
    ITAMED_AVAILABLE = True
except ImportError as e:
    ITAMED_AVAILABLE = False

# Try to import ITAMeD L2 if available (only if source .py file exists)
ITAMED_L2_AVAILABLE = False
itamed_l2_version = None
try:
    # Only try to import if .py file exists (not just .pyc)
    from pathlib import Path
    l2_py_path = Path(__file__).parent / "itamed_l2_version.py"
    if l2_py_path.exists():
        from . import itamed_l2_version
        ITAMED_L2_AVAILABLE = True
except (ImportError, AttributeError):
    ITAMED_L2_AVAILABLE = False
    itamed_l2_version = None

# Export what's available
__all__ = [
    "processing",
    "ITAMED_AVAILABLE",
    "ITAMED_L2_AVAILABLE",
]

# Conditionally add itamed_l2_version to exports if available
if ITAMED_L2_AVAILABLE and itamed_l2_version is not None:
    __all__.append("itamed_l2_version")

