"""
ITAMeD Processing Module

This module provides access to the ITAMeD core processing functions.
It wraps the core module to match the expected import structure.
This allows imports like: from external_packages.processing import core
or: import external_packages.processing.core as itamed
"""

# Import the core module
from . import core

# Make core available as a submodule
# This allows: import processing.core as itamed
__all__ = ['core']

