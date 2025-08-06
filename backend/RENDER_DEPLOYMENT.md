# Render Deployment Guide

## Problem
PyMuPDF compilation fails on Render due to missing C++ dependencies and environment differences.

## Solutions Implemented

### 1. Alternative Requirements File
- `requirements-render.txt` - Excludes PyMuPDF for reliable deployment
- `requirements.txt` - Full requirements for local development

### 2. Build Script
- `build.sh` - Handles dependency installation gracefully
- Tries to install PyMuPDF but continues without it if it fails

### 3. Alternative PDF Processor
- `alternative_pdf_processor.py` - Uses pdfplumber and PyPDF2 instead of PyMuPDF
- Provides similar functionality without compilation issues

## Render Configuration

### Build Command
```bash
chmod +x build.sh && ./build.sh
```

### Start Command
```bash
uvicorn main:app --host 0.0.0.0 --port $PORT
```

### Environment Variables
Set these in your Render dashboard:
- `PORT` (automatically set by Render)
- `GOOGLE_API_KEY`
- `PINECONE_API_KEY`
- `PINECONE_ENVIRONMENT`
- `MONGODB_URL`
- `SECRET_KEY`
- Other environment variables as needed

## Testing PDF Processing

The application will automatically detect available PDF processors:
1. **pdfplumber** (primary) - Best text extraction
2. **PyPDF2** (fallback) - Reliable for most PDFs
3. **pdfminer** (additional) - Good for complex layouts
4. **PyMuPDF** (optional) - Will use if available

## Local vs Production Differences

### Local Development
- Can use PyMuPDF with pre-compiled wheels
- Full requirements.txt

### Production (Render)
- Uses requirements-render.txt (no PyMuPDF)
- Alternative PDF processors
- Same functionality, different implementation

## Troubleshooting

If deployment still fails:

1. **Use requirements-render.txt only**:
   ```bash
   pip install -r requirements-render.txt
   ```

2. **Check logs for specific package failures**:
   - Look for individual package installation errors
   - Pin specific versions if needed

3. **Test PDF processing**:
   ```python
   # Test available processors
   import logging
   logging.basicConfig(level=logging.INFO)
   
   # Upload a test PDF to verify functionality
   ```
