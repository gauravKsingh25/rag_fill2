"""
File Cleanup Service

This service manages the cleanup of temporary files created during document and CSV processing.
Files are stored locally for download purposes but should be cleaned up after download since
they are already backed up to GCS via the file history service.

Key Features:
- Automatic cleanup after download with configurable delay
- Manual cleanup endpoints for immediate cleanup
- Age-based cleanup for old files
- Configurable cleanup policies
"""

import os
import time
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class FileCleanupService:
    """Service for cleaning up temporary files after they've been downloaded"""
    
    def __init__(self):
        self.filled_templates_dir = Path("./filled_templates")
        self.filled_templates_dir.mkdir(exist_ok=True)
        
        # Cleanup configuration
        self.default_cleanup_delay_seconds = 30  # 30 seconds after download
        self.max_file_age_hours = 24  # Clean up files older than 24 hours
        self.cleanup_batch_size = 50  # Process this many files at once
    
    async def schedule_file_cleanup(self, file_path: str, delay_seconds: Optional[int] = None) -> None:
        """
        Schedule a file for cleanup after a delay.
        This is used after file downloads to clean up the local copy.
        
        Args:
            file_path: Path to the file to clean up
            delay_seconds: Delay before cleanup (default: 30 seconds)
        """
        delay = delay_seconds or self.default_cleanup_delay_seconds
        
        async def cleanup_task():
            try:
                await asyncio.sleep(delay)
                file_path_obj = Path(file_path)
                
                if file_path_obj.exists():
                    file_path_obj.unlink()
                    logger.info(f"🧹 Cleaned up file after download: {file_path_obj.name}")
                else:
                    logger.debug(f"File already removed: {file_path_obj.name}")
                    
            except Exception as e:
                logger.warning(f"⚠️ Failed to cleanup file {file_path}: {e}")
        
        # Schedule the cleanup task in the background
        asyncio.create_task(cleanup_task())
        logger.info(f"📅 Scheduled cleanup for {Path(file_path).name} in {delay} seconds")
    
    async def cleanup_old_files(self, max_age_hours: Optional[int] = None) -> Dict[str, Any]:
        """
        Clean up files older than the specified age.
        
        Args:
            max_age_hours: Files older than this will be removed (default: 24 hours)
            
        Returns:
            Dict with cleanup results
        """
        max_age = max_age_hours or self.max_file_age_hours
        cutoff_time = time.time() - (max_age * 3600)
        
        cleaned_files = []
        total_size_cleaned = 0
        errors = []
        
        try:
            if not self.filled_templates_dir.exists():
                return {
                    'success': True,
                    'cleaned_files': [],
                    'total_cleaned': 0,
                    'total_size_mb': 0,
                    'message': 'No filled templates directory found'
                }
            
            # Find old files
            for file_path in self.filled_templates_dir.iterdir():
                if not file_path.is_file():
                    continue
                
                try:
                    # Check file age
                    file_stat = file_path.stat()
                    if file_stat.st_mtime < cutoff_time:
                        file_size = file_stat.st_size
                        file_path.unlink()
                        
                        cleaned_files.append({
                            'filename': file_path.name,
                            'size_bytes': file_size,
                            'age_hours': (time.time() - file_stat.st_mtime) / 3600
                        })
                        total_size_cleaned += file_size
                        logger.info(f"🧹 Cleaned old file: {file_path.name}")
                        
                except Exception as e:
                    error_msg = f"Failed to cleanup {file_path.name}: {e}"
                    errors.append(error_msg)
                    logger.warning(f"⚠️ {error_msg}")
            
            return {
                'success': True,
                'cleaned_files': cleaned_files,
                'total_cleaned': len(cleaned_files),
                'total_size_mb': round(total_size_cleaned / (1024 * 1024), 2),
                'errors': errors,
                'message': f'Cleaned {len(cleaned_files)} old files ({round(total_size_cleaned / (1024 * 1024), 2)} MB)'
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to cleanup old files: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to cleanup old files'
            }
    
    async def cleanup_all_files(self) -> Dict[str, Any]:
        """
        Clean up all files in the filled templates directory.
        Use with caution - this removes all local copies.
        
        Returns:
            Dict with cleanup results
        """
        cleaned_files = []
        total_size_cleaned = 0
        errors = []
        
        try:
            if not self.filled_templates_dir.exists():
                return {
                    'success': True,
                    'cleaned_files': [],
                    'total_cleaned': 0,
                    'total_size_mb': 0,
                    'message': 'No filled templates directory found'
                }
            
            # Clean all files
            for file_path in self.filled_templates_dir.iterdir():
                if not file_path.is_file():
                    continue
                
                try:
                    file_size = file_path.stat().st_size
                    file_path.unlink()
                    
                    cleaned_files.append({
                        'filename': file_path.name,
                        'size_bytes': file_size
                    })
                    total_size_cleaned += file_size
                    logger.info(f"🧹 Cleaned file: {file_path.name}")
                    
                except Exception as e:
                    error_msg = f"Failed to cleanup {file_path.name}: {e}"
                    errors.append(error_msg)
                    logger.warning(f"⚠️ {error_msg}")
            
            return {
                'success': True,
                'cleaned_files': cleaned_files,
                'total_cleaned': len(cleaned_files),
                'total_size_mb': round(total_size_cleaned / (1024 * 1024), 2),
                'errors': errors,
                'message': f'Cleaned all {len(cleaned_files)} files ({round(total_size_cleaned / (1024 * 1024), 2)} MB)'
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to cleanup all files: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to cleanup all files'
            }
    
    async def cleanup_specific_file(self, filename: str) -> Dict[str, Any]:
        """
        Clean up a specific file by filename.
        
        Args:
            filename: Name of the file to clean up
            
        Returns:
            Dict with cleanup result
        """
        try:
            file_path = self.filled_templates_dir / filename
            
            if not file_path.exists():
                return {
                    'success': True,
                    'message': f'File {filename} not found (already cleaned or never existed)'
                }
            
            file_size = file_path.stat().st_size
            file_path.unlink()
            
            logger.info(f"🧹 Cleaned specific file: {filename}")
            
            return {
                'success': True,
                'filename': filename,
                'size_bytes': file_size,
                'size_mb': round(file_size / (1024 * 1024), 2),
                'message': f'Successfully cleaned {filename}'
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to cleanup file {filename}: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': f'Failed to cleanup {filename}'
            }
    
    async def get_storage_info(self) -> Dict[str, Any]:
        """
        Get information about the current storage usage.
        
        Returns:
            Dict with storage information
        """
        try:
            if not self.filled_templates_dir.exists():
                return {
                    'total_files': 0,
                    'total_size_mb': 0,
                    'files': [],
                    'message': 'No filled templates directory found'
                }
            
            files_info = []
            total_size = 0
            
            for file_path in self.filled_templates_dir.iterdir():
                if not file_path.is_file():
                    continue
                
                try:
                    file_stat = file_path.stat()
                    file_info = {
                        'filename': file_path.name,
                        'size_bytes': file_stat.st_size,
                        'size_mb': round(file_stat.st_size / (1024 * 1024), 2),
                        'created_time': datetime.fromtimestamp(file_stat.st_ctime).isoformat(),
                        'modified_time': datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
                        'age_hours': round((time.time() - file_stat.st_mtime) / 3600, 2)
                    }
                    files_info.append(file_info)
                    total_size += file_stat.st_size
                    
                except Exception as e:
                    logger.warning(f"⚠️ Failed to get info for {file_path.name}: {e}")
            
            # Sort by age (newest first)
            files_info.sort(key=lambda x: x['age_hours'])
            
            return {
                'total_files': len(files_info),
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'files': files_info,
                'cleanup_recommendations': {
                    'old_files_count': len([f for f in files_info if f['age_hours'] > self.max_file_age_hours]),
                    'should_cleanup': len(files_info) > 10 or total_size > 100 * 1024 * 1024  # More than 10 files or 100MB
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get storage info: {e}")
            return {
                'error': str(e),
                'message': 'Failed to get storage information'
            }

    async def startup_cleanup(self) -> Dict[str, Any]:
        """
        Perform cleanup on application startup to remove any leftover files.
        This ensures the application starts with a clean slate.
        """
        try:
            logger.info("🧹 Performing startup cleanup of old files...")
            
            # Clean up files older than 1 hour (more aggressive on startup)
            result = await self.cleanup_old_files(max_age_hours=1)
            
            if result['success'] and result['total_cleaned'] > 0:
                logger.info(f"✅ Startup cleanup completed: {result['message']}")
            elif result['success']:
                logger.info("✅ Startup cleanup: No old files found")
            else:
                logger.warning(f"⚠️ Startup cleanup had issues: {result.get('message', 'Unknown error')}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to perform startup cleanup: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to perform startup cleanup'
            }

# Global instance
file_cleanup_service = FileCleanupService()
