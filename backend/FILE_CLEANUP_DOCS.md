# File Cleanup System Documentation

## Overview

The file cleanup system addresses the issue where filled documents and CSVs were being saved to local storage and accumulating over time. While these files are needed temporarily for download purposes, they were not being cleaned up after download, leading to storage bloat.

## Problem Statement

- Filled documents and CSVs are saved locally in `./filled_templates/` directory for download
- Files are also backed up to GCS via the file history service
- Local files were not being cleaned up after download
- This resulted in storage accumulation and potential disk space issues

## Solution

The solution implements a comprehensive file cleanup system with the following components:

### 1. File Cleanup Service (`app/services/file_cleanup_service.py`)

**Features:**
- **Automatic cleanup after download** with configurable delay (default: 30 seconds)
- **Age-based cleanup** for files older than specified hours (default: 24 hours)
- **Manual cleanup** for specific files or all files
- **Storage monitoring** to track usage and provide recommendations
- **Startup cleanup** to remove leftover files from previous sessions

**Key Methods:**
- `schedule_file_cleanup()` - Schedule cleanup after download
- `cleanup_old_files()` - Remove files older than specified age
- `cleanup_all_files()` - Remove all local files (use with caution)
- `get_storage_info()` - Get current storage usage information

### 2. File Cleanup Router (`app/routers/file_cleanup.py`)

**Endpoints:**
- `GET /api/file-cleanup/storage-info` - View current storage usage
- `POST /api/file-cleanup/cleanup-old` - Clean files older than X hours
- `POST /api/file-cleanup/cleanup-all` - Clean all files (use with caution)
- `DELETE /api/file-cleanup/cleanup/{filename}` - Clean specific file
- `POST /api/file-cleanup/auto-cleanup` - Trigger automatic cleanup based on policies

### 3. Enhanced Download Endpoints

**Modified endpoints to include automatic cleanup:**
- `/api/templates/download/{filename}` - Download filled template with cleanup
- `/api/templates/download-csv/{filename}` - Download filled CSV with cleanup
- `/api/download/{filename}` (deterministic router) - Download with cleanup

**How it works:**
1. User downloads file
2. Background task is scheduled to clean up the file after 30 seconds
3. File is removed from local storage while GCS backup remains intact

### 4. Startup Cleanup

**On application startup:**
- Automatically cleans up files older than 1 hour
- Ensures the application starts with a clean slate
- Logs cleanup results for monitoring

## Configuration

### Default Settings
```python
default_cleanup_delay_seconds = 30  # Delay after download
max_file_age_hours = 24            # Age threshold for cleanup
cleanup_batch_size = 50            # Batch processing size
```

### Cleanup Policies
- **Post-download**: Files are cleaned 30 seconds after download
- **Age-based**: Files older than 24 hours are eligible for cleanup
- **Startup**: Files older than 1 hour are cleaned on startup
- **Auto-cleanup**: Triggered when >10 files or >100MB total size

## Benefits

1. **Storage Optimization**: Prevents local storage accumulation
2. **Data Safety**: GCS backups ensure no data loss
3. **Performance**: Reduced local storage improves system performance
4. **Automation**: Minimal manual intervention required
5. **Monitoring**: Storage info and cleanup statistics available

## Usage Examples

### Check Storage Usage
```bash
GET /api/file-cleanup/storage-info
```

### Clean Old Files
```bash
POST /api/file-cleanup/cleanup-old?max_age_hours=12
```

### Manual Cleanup of Specific File
```bash
DELETE /api/file-cleanup/cleanup/filled_abc123_document.docx
```

### Trigger Auto-Cleanup
```bash
POST /api/file-cleanup/auto-cleanup
```

## Important Notes

1. **GCS Backup**: All files are backed up to GCS before local cleanup
2. **Download Safety**: 30-second delay ensures download completion
3. **Recovery**: Files can be accessed from GCS via file history
4. **Monitoring**: All cleanup operations are logged for auditing

## Migration Impact

- **Existing files**: Will be cleaned up gradually by age-based cleanup
- **User experience**: No change - downloads work exactly the same
- **Storage**: Significant reduction in local storage usage
- **Performance**: Improved system performance due to less local storage

This system ensures efficient storage management while maintaining data integrity and user experience.
