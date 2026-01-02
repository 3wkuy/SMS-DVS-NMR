"""
External Packages for CPMG NMR Analysis

This module includes third-party packages bundled with the main package.
Currently includes: ITAMeD (Inverse Laplace Transform library)
"""

# Import ITAMeD processing module
try:
    from . import processing
    print("  [BUNDLED] ITAMeD processing module loaded")
    ITAMED_AVAILABLE = True
except ImportError as e:
    print(f"  [BUNDLED] ITAMeD processing module not found: {e}")
    ITAMED_AVAILABLE = False

# Try to import ITAMeD L2 if available
ITAMED_L2_AVAILABLE = False
try:
    from . import itamed_l2_version
    print("  [BUNDLED] ITAMeD L2 version loaded")
    ITAMED_L2_AVAILABLE = True
except ImportError as e:
    print(f"  [BUNDLED] ITAMeD L2 version not found: {e}")
    ITAMED_L2_AVAILABLE = False

# Export what's available
__all__ = [
    "processing",
    "itamed_l2_version",
    "ITAMED_AVAILABLE",
    "ITAMED_L2_AVAILABLE",
]

