# GitHub Installation Guide

This guide explains how to install mehiamlonely directly from GitHub using pip.

## 🚀 Quick Installation

```bash
# Install directly from GitHub
pip install git+https://github.com/yourusername/mehiamlonely.git

# Or install from a specific branch/tag
pip install git+https://github.com/yourusername/mehiamlonely.git@main
pip install git+https://github.com/yourusername/mehiamlonely.git@v0.1.0
```

## 📋 Prerequisites

- Python 3.8 or higher
- Git installed on your system
- pip (Python package installer)

## 🔧 Installation Methods

### Method 1: Direct GitHub Installation
```bash
# Install from main branch
pip install git+https://github.com/yourusername/mehiamlonely.git

# Install from specific branch
pip install git+https://github.com/yourusername/mehiamlonely.git@develop

# Install from specific tag/version
pip install git+https://github.com/yourusername/mehiamlonely.git@v0.1.0
```

### Method 2: Clone and Install
```bash
# Clone the repository
git clone https://github.com/yourusername/mehiamlonely.git
cd mehiamlonely

# Install in development mode
pip install -e .

# Or install normally
pip install .
```

### Method 3: Install with Dependencies
```bash
# Install with all dependencies
pip install git+https://github.com/yourusername/mehiamlonely.git

# Install with development dependencies
pip install git+https://github.com/yourusername/mehiamlonely.git[dev]
```

## ✅ Verify Installation

After installation, verify it works:

```bash
# Check if mehiamlonely is installed
mehiamlonely --help

# Test with a server URL
mehiamlonely --test-connection https://your-server.onrender.com/
```

## 🔄 Updating

To update to the latest version:

```bash
# Update from GitHub
pip install --upgrade git+https://github.com/yourusername/mehiamlonely.git

# Or reinstall
pip uninstall mehiamlonely
pip install git+https://github.com/yourusername/mehiamlonely.git
```

## 🛠️ Development Installation

For development work:

```bash
# Clone and install in editable mode
git clone https://github.com/yourusername/mehiamlonely.git
cd mehiamlonely
pip install -e .[dev]

# This allows you to modify the code and see changes immediately
```

## 📦 Package Structure

The package includes:
- `setup.py` - Installation script
- `pyproject.toml` - Modern Python packaging configuration
- `MANIFEST.in` - Files to include in the package
- `LICENSE` - MIT license
- `README.md` - Package documentation
- `src/mehiamlonely/` - Source code
- `USAGE.md` - Usage examples

## 🐛 Troubleshooting

### Common Issues

1. **Git not found:**
   ```bash
   # Install Git first
   # macOS: brew install git
   # Ubuntu: sudo apt install git
   # Windows: Download from https://git-scm.com/
   ```

2. **Permission errors:**
   ```bash
   # Use --user flag
   pip install --user git+https://github.com/yourusername/mehiamlonely.git
   ```

3. **SSL certificate errors:**
   ```bash
   # Use --trusted-host flag
   pip install --trusted-host github.com git+https://github.com/yourusername/mehiamlonely.git
   ```

4. **Network issues:**
   ```bash
   # Use SSH instead of HTTPS (if you have SSH keys set up)
   pip install git+ssh://git@github.com/yourusername/mehiamlonely.git
   ```

### Debug Installation

```bash
# Install with verbose output
pip install -v git+https://github.com/yourusername/mehiamlonely.git

# Check what's installed
pip show mehiamlonely

# List all installed packages
pip list | grep mehiamlonely
```

## 🔒 Security Considerations

- Always verify the repository URL before installing
- Check the repository for any suspicious code
- Consider using specific tags/versions instead of main branch
- Review the LICENSE file

## 📚 Usage After Installation

Once installed, you can use mehiamlonely:

```bash
# Basic usage
mehiamlonely https://your-server.onrender.com/

# With options
mehiamlonely --upload-files --verbose https://your-server.onrender.com/

# Test connection
mehiamlonely --test-connection https://your-server.onrender.com/
```

## 🆘 Getting Help

If you encounter issues:

1. Check the repository README
2. Look at the Issues page on GitHub
3. Verify your Python version: `python --version`
4. Check pip version: `pip --version`
5. Try installing in a virtual environment

## 📝 Notes

- The package is configured to work with both `setup.py` and `pyproject.toml`
- All necessary files are included via `MANIFEST.in`
- The package follows Python packaging best practices
- Compatible with Python 3.8+ and modern pip versions
