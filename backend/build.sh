#!/bin/bash

# Render build script for handling dependencies

set -e

echo "Starting build process..."

# Upgrade pip first
pip install --upgrade pip

# Install wheel 
pip install wheel

# Try to install from requirements-render.txt first (without PyMuPDF)
if [ -f "requirements-render.txt" ]; then
    echo "Installing from requirements-render.txt (without PyMuPDF)..."
    pip install -r requirements-render.txt
else
    echo "Installing from requirements.txt..."
    # Try to install without PyMuPDF first
    grep -v -i pymupdf requirements.txt > temp_requirements.txt || cp requirements.txt temp_requirements.txt
    pip install -r temp_requirements.txt
    rm -f temp_requirements.txt
fi

# Try to install PyMuPDF with specific options
echo "Attempting to install PyMuPDF..."
pip install --only-binary=all PyMuPDF==1.23.8 || {
    echo "PyMuPDF installation failed, continuing without it..."
    echo "The application will use alternative PDF processors (pdfplumber, PyPDF2, pdfminer)"
}

echo "Build process completed!"
echo "Available PDF processors:"
python -c "
try:
    import PyPDF2
    print('✓ PyPDF2 available')
except ImportError:
    print('✗ PyPDF2 not available')

try:
    import pdfplumber
    print('✓ pdfplumber available')
except ImportError:
    print('✗ pdfplumber not available')

try:
    import fitz
    print('✓ PyMuPDF available')
except ImportError:
    print('✗ PyMuPDF not available (expected)')

try:
    import pdfminer
    print('✓ pdfminer available')
except ImportError:
    print('✗ pdfminer not available')
"
