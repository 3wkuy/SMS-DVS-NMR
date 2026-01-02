"""
Setup script for CPMG NMR Data Processing Package
"""
from setuptools import setup, find_packages
import sys

# Read the requirements
with open('requirements.txt', 'r') as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]

setup(
    name="nmr-cpmg-analysis",
    version="1.3.0",
    description="CPMG NMR Data Processing with Advanced ILT Analysis",
    long_description="""
    A comprehensive Python package for processing CPMG NMR data from TNMR software.
    Features include:
    - T2 fitting and analysis
    - Inverse Laplace Transform (ILT) with automatic lambda optimization
    - Multiple datasets support with configurable processing parameters
    - Batch processing capabilities
    - Rich visualization and reporting
    """,
    author="Your Name",
    python_requires=">=3.7",
    packages=find_packages(),
    install_requires=requirements,
    entry_points={
        'console_scripts': [
            'nmr-cpmg=nmr_cpmg_analysis:main',
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Physics",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)

