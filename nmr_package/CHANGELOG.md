# Changelog

All notable changes to the CPMG NMR Data Processing Package will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.3.0] - 2025-01-02

### Added
- Initial packaged release of the CPMG NMR analysis software
- Automated installation scripts for Windows (install.bat) and Linux/Mac (install.sh)
- Comprehensive documentation (README, USER_GUIDE, QUICKSTART)
- Pre-configured dataset support (10 datasets included)
- Cross-platform compatibility (Windows, Linux, Mac)
- Easy-to-use interface with run_nmr_analysis.py script
- Setup.py for package distribution
- Enhanced error handling and user feedback

### Features
- ILT analysis with RMEA1D and ITAMeD methods
- Automatic lambda optimization using L-curve and balanced methods
- Batch processing capabilities
- Rich visualization (T2 distributions, L-curves, peak integration)
- Peak analysis and integration
- Data truncation support
- Multi-dataset support with easy configuration

### Documentation
- README.md: Comprehensive overview and quick start
- USER_GUIDE.md: Detailed user guide with examples and troubleshooting
- QUICKSTART.md: Simplified getting started guide
- CHANGELOG.md: Version history
- LICENSE: MIT license

### Improved
- Better error messages and user guidance
- Graceful fallback when ITAMeD is not available
- Automatic dependency checking
- Cross-platform path handling
- Progress indicators during processing

### Dependencies
- numpy >= 1.21.0
- matplotlib >= 3.5.0
- scipy >= 1.7.0
- pandas >= 1.3.0
- pywin32 >= 305 (Windows only, optional)

### Known Issues
- ITAMeD module requires manual installation from separate repository
- pywin32 installation may require post-install script on Windows
- Large datasets may require significant memory

## [Unreleased]

### Planned Features
- [ ] GUI interface for non-technical users
- [ ] Web-based interface
- [ ] Additional NMR analysis methods
- [ ] Support for more file formats
- [ ] Parallel processing for faster batch processing
- [ ] Cloud-based analysis option
- [ ] Interactive plot customization
- [ ] Export to additional formats (HDF5, Parquet)
- [ ] T1 relaxation analysis support
- [ ] Multi-dimensional NMR support

### Planned Improvements
- [ ] Enhanced memory optimization for large datasets
- [ ] Faster ILT algorithms
- [ ] More robust error recovery
- [ ] Better handling of edge cases
- [ ] Improved documentation with video tutorials
- [ ] Example datasets for testing

---

## Version History

### Previous Versions
The package was originally developed as a standalone script for specific research projects at Imperial College London. The codebase has been continuously improved and refactored to support:

- Multiple research projects
- Various NMR datasets (LiCl, Mg(NO3)2, Lewatit, Urea, Avicel)
- Different NMR instruments and field strengths (0.5T, 0.8T, 1.5T)
- Multiple researchers with different needs

This packaged version (1.3.0) represents the first release as a redistributable Python package with full documentation and automated installation.

---

## Release Notes by Version

### 1.3.0 - January 2025
**Major Release: First Packaged Version**

This version transforms the research code into a user-friendly package:

- Easy installation with one command
- No manual dependency management required
- Clear documentation for new users
- Cross-platform support
- Pre-configured datasets for common research scenarios
- Comprehensive error handling and troubleshooting guides

**Target Audience**: Researchers new to NMR analysis who want a plug-and-play solution.

---

## Upgrade Guide

### From 1.x to 1.3.0
If you have been using the raw script version:

1. Download the new package
2. Install dependencies using install.bat or install.sh
3. Copy your custom dataset configurations if any
4. Run using: `python run_nmr_analysis.py`
5. Results will be in the same format as before

No changes to your data or analysis methodology are required.

---

## Migration Guide

### For Script Users

If you were using the raw script:

**Old way:**
```bash
python merged_CPMG_ILT_analysis_v1.3.py --mode all --start 1 --end 100
```

**New way:**
```bash
python run_nmr_analysis.py --mode all --start 1 --end 100
```

**For Python code:**

**Old way:**
```python
import merged_CPMG_ILT_analysis_v1_3 as analysis
analysis.perform_ilt(t, m, tau, lambda_value)
```

**New way:**
```python
from nmr_cpmg_analysis import perform_ilt
perform_ilt(t, m, tau, lambda_value)
```

The API remains the same, just with better packaging.

---

## Contributing

To contribute to this package:

1. Check the [CHANGELOG.md](CHANGELOG.md) for planned features
2. Follow the contribution guidelines
3. Submit pull requests with clear descriptions
4. Update documentation as needed
5. Add tests for new features

---

## Roadmap

### Short-term (3-6 months)
- Add unit tests
- Improve documentation with more examples
- Add video tutorials
- Enhance error messages
- Add more pre-configured datasets

### Medium-term (6-12 months)
- Develop GUI interface
- Add parallel processing
- Support additional file formats
- Create interactive web interface
- Add cloud integration

### Long-term (1+ years)
- Multi-dimensional NMR analysis
- T1 relaxation support
- Advanced visualization
- Machine learning integration
- Automated analysis suggestions

---

## Support Policy

### Version Support
- Current version (1.3.x): Full support, active development
- Previous versions: Security fixes only
- End of life: No support

### Issue Response Time
- Critical bugs: 24-48 hours
- Major issues: 1 week
- Minor issues: 2 weeks
- Feature requests: As time permits

### Platform Support
- Windows 10/11: Fully supported
- macOS 10.15+: Fully supported
- Linux (Ubuntu 20.04+, Debian 10+, Fedora 33+): Fully supported
- Other platforms: Best effort

---

**For older versions, please refer to the respective version documentation.**

