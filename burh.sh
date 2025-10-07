#!/bin/bash

# Exit on any error
set -e

# Define the source and destination directories
PROJECT_ROOT=$(pwd)
SRC_DIR="$PROJECT_ROOT/src"
PACKAGE_DIR="$SRC_DIR/mehiamlonely"

# Create src and package directories if they don't exist
mkdir -p "$PACKAGE_DIR"

# Move and rename Python files
mv "$PROJECT_ROOT/mehiamlonely_main.py" "$PACKAGE_DIR/extractor.py" 2>/dev/null || echo "mehiamlonely_main.py not found, skipping"
mv "$PROJECT_ROOT/upload.py" "$PACKAGE_DIR/uploader.py" 2>/dev/null || echo "upload.py not found, skipping"
mv "$PROJECT_ROOT/test.py" "$PACKAGE_DIR/test.py" 2>/dev/null || echo "test.py not found, skipping"
mv "$PROJECT_ROOT/tests.py" "$PACKAGE_DIR/tests.py" 2>/dev/null || echo "tests.py not found, skipping"

# Handle tests directory (if it exists as a folder)
if [ -d "$PROJECT_ROOT/tests" ]; then
    mv "$PROJECT_ROOT/tests" "$PACKAGE_DIR/tests"
    # Create __init__.py inside tests if it doesn't exist
    touch "$PACKAGE_DIR/tests/__init__.py" 2>/dev/null || echo "Failed to create tests/__init__.py"
fi

# Create __init__.py in the package directory
touch "$PACKAGE_DIR/__init__.py" 2>/dev/null || echo "Failed to create __init__.py"

# Create cli.py if it doesn't exist
touch "$PACKAGE_DIR/cli.py" 2>/dev/null || echo "Failed to create cli.py"

# Ensure pyproject.toml, LICENSE, and README.md stay in root
# (Assuming they are already in root; no action needed unless moved)

echo "Folder structure updated successfully!"
echo "New structure:"
tree "$PROJECT_ROOT" || echo "Install 'tree' command for a visual structure, or check manually."