from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
import logging
import os
import sys
from pathlib import Path

# Get logger instance
logger = logging.getLogger(__name__)

router = APIRouter(tags=["cache"])

@router.post("/clear-cache")
async def clear_cache_endpoint():
    """API endpoint to clear metadata cache"""
    # Add parent directory to path to import from app.py
    sys.path.append(str(Path(__file__).parent.parent.parent))
    from app import clear_metadata_cache
    try:
        clear_metadata_cache()
        return JSONResponse(
            status_code=200,
            content={"success": True, "message": "Cache cleared successfully"}
        )
    except Exception as e:
        logger.error(f"Error clearing cache via API: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

@router.post("/cleanup-cache")
async def cleanup_cache_endpoint():
    """API endpoint to cleanup stale cache entries"""
    try:
        from cache_management import get_cache_service
        cache_service = get_cache_service()
        cleaned_count = cache_service.cleanup_cache()
        return JSONResponse(
            status_code=200,
            content={
                "success": True, 
                "message": f"Cache cleanup completed. Removed {cleaned_count} stale entries.",
                "cleaned_count": cleaned_count
            }
        )
    except Exception as e:
        logger.error(f"Error cleaning up cache via API: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

@router.get("/cache-stats")
async def cache_stats_endpoint():
    """API endpoint to get cache statistics"""
    try:
        from cache_management import get_cache_service
        cache_service = get_cache_service()
        stats = cache_service.get_cache_stats()
        return JSONResponse(
            status_code=200,
            content={"success": True, "stats": stats}
        )
    except Exception as e:
        logger.error(f"Error getting cache stats via API: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

@router.post("/restart-file-watcher")
async def restart_file_watcher_endpoint():
    """API endpoint to restart the file watcher"""
    try:
        from cache_management import get_cache_service
        cache_service = get_cache_service()
        cache_service.restart_file_watcher()
        return JSONResponse(
            status_code=200,
            content={"success": True, "message": "File watcher restarted successfully"}
        )
    except Exception as e:
        logger.error(f"Error restarting file watcher via API: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

@router.post("/cleanup-duplicate-filenames")
async def cleanup_duplicate_filenames_endpoint():
    """API endpoint to cleanup duplicate filenames in different directories"""
    try:
        from cache_management import get_cache_service
        cache_service = get_cache_service()
        cache_manager = cache_service.cache_manager
        
        # Load current mappings
        mappings = cache_manager.load_file_mappings()
        original_count = len(mappings)
        
        # Group by filename
        filename_groups = {}
        for path in mappings.keys():
            filename = os.path.basename(path)
            if filename not in filename_groups:
                filename_groups[filename] = []
            filename_groups[filename].append(path)
        
        # Remove duplicates - keep the most recent one (last modified)
        paths_to_remove = []
        for filename, paths in filename_groups.items():
            if len(paths) > 1:
                # Sort by modification time of the actual files if they exist
                # Otherwise, keep the path that was added most recently
                paths_with_times = []
                for path in paths:
                    if os.path.exists(path):
                        mtime = os.path.getmtime(path)
                        paths_with_times.append((path, mtime))
                    else:
                        # File doesn't exist, mark for removal
                        paths_to_remove.append(path)
                
                # If we have existing files, keep the newest one
                if paths_with_times:
                    paths_with_times.sort(key=lambda x: x[1], reverse=True)
                    # Remove all but the newest
                    for path, _ in paths_with_times[1:]:
                        paths_to_remove.append(path)
                # If no files exist, remove all but the last one in the list
                elif len(paths) > 1:
                    paths_to_remove.extend(paths[:-1])
        
        # Remove the duplicate mappings
        for path_to_remove in paths_to_remove:
            if path_to_remove in mappings:
                del mappings[path_to_remove]
                cache_manager.cleanup_stale_metadata_cache([path_to_remove])
        
        # Save updated mappings
        cache_manager.save_file_mappings(mappings)
        
        cleaned_count = len(paths_to_remove)
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": f"Cleaned up {cleaned_count} duplicate filename mappings",
                "original_count": original_count,
                "cleaned_count": cleaned_count,
                "remaining_count": len(mappings),
                "removed_paths": paths_to_remove
            }
        )
    except Exception as e:
        logger.error(f"Error cleaning duplicate filenames via API: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

@router.post("/cleanup-same-directory-files")
async def cleanup_same_directory_files_endpoint():
    """API endpoint to cleanup files in the same directory (handles renames)"""
    try:
        from cache_management import get_cache_service
        cache_service = get_cache_service()
        cache_manager = cache_service.cache_manager
        
        # Load current mappings
        mappings = cache_manager.load_file_mappings()
        original_count = len(mappings)
        
        # Group by directory
        directory_groups = {}
        for path in mappings.keys():
            directory = os.path.dirname(path)
            if directory not in directory_groups:
                directory_groups[directory] = []
            directory_groups[directory].append(path)
        
        # For each directory, if there are multiple files, keep only the newest
        paths_to_remove = []
        for directory, paths in directory_groups.items():
            if len(paths) > 1:
                logger.info(f"Found {len(paths)} files in directory {directory}")
                
                # Check which files exist and get their modification times
                existing_paths = []
                non_existing_paths = []
                
                for path in paths:
                    temp_path = mappings[path]
                    if os.path.exists(temp_path):
                        try:
                            mtime = os.path.getmtime(temp_path)
                            existing_paths.append((path, mtime))
                        except OSError:
                            non_existing_paths.append(path)
                    else:
                        non_existing_paths.append(path)
                
                # Remove all non-existing files
                paths_to_remove.extend(non_existing_paths)
                
                # If we have existing files, keep only the newest one
                if existing_paths:
                    existing_paths.sort(key=lambda x: x[1], reverse=True)
                    # Remove all but the newest
                    for path, _ in existing_paths[1:]:
                        paths_to_remove.append(path)
                        logger.info(f"Removing older file in same directory: {path}")
        
        # Remove the selected mappings
        for path_to_remove in paths_to_remove:
            if path_to_remove in mappings:
                del mappings[path_to_remove]
                cache_manager.cleanup_stale_metadata_cache([path_to_remove])
        
        # Save updated mappings
        cache_manager.save_file_mappings(mappings)
        
        cleaned_count = len(paths_to_remove)
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": f"Cleaned up {cleaned_count} files in same directories",
                "original_count": original_count,
                "cleaned_count": cleaned_count,
                "remaining_count": len(mappings),
                "removed_paths": paths_to_remove
            }
        )
    except Exception as e:
        logger.error(f"Error cleaning same directory files via API: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )
