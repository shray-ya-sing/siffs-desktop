from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any, Optional
import logging
import os
from pathlib import Path

from services.slide_processing_service import get_slide_processing_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/slides", tags=["slides"])

# Request/Response models
class ProcessFolderRequest(BaseModel):
    folder_path: str

class ProcessFolderResponse(BaseModel):
    success: bool
    message: str
    files_processed: int
    slides_processed: int
    failed_files: Optional[list] = []
    error: Optional[str] = None

# Global variable to track processing status
_processing_status = {
    'is_processing': False,
    'current_file': '',
    'progress': 0.0,
    'files_processed': 0,
    'slides_processed': 0
}

def update_progress(progress_data: Dict[str, Any]):
    """Update global processing status"""
    global _processing_status
    _processing_status.update(progress_data)
    _processing_status['is_processing'] = progress_data.get('status') != 'completed'
    logger.info(f"Processing progress: {progress_data}")

@router.post("/process-folder", response_model=ProcessFolderResponse)
async def process_folder(request: ProcessFolderRequest, background_tasks: BackgroundTasks):
    """
    Process all PowerPoint files in a folder
    
    This endpoint:
    1. Scans the folder for .pptx files
    2. Converts slides to images using COM automation
    3. Creates multimodal embeddings using VoyageAI
    4. Stores embeddings in Pinecone vector database
    """
    try:
        # Log the received path for debugging
        logger.info(f"Received folder path: '{request.folder_path}'")
        logger.info(f"Path type: {type(request.folder_path)}")
        logger.info(f"Path repr: {repr(request.folder_path)}")
        
        # Clean the path to handle common issues
        cleaned_path = request.folder_path.strip()  # Remove leading/trailing whitespace
        
        # Remove surrounding quotes if present
        if (cleaned_path.startswith('"') and cleaned_path.endswith('"')) or \
           (cleaned_path.startswith("'") and cleaned_path.endswith("'")):
            cleaned_path = cleaned_path[1:-1]
            logger.info(f"Removed quotes from path: '{cleaned_path}'")
        
        # Normalize the path to handle different formats
        normalized_path = os.path.normpath(cleaned_path)
        logger.info(f"Cleaned path: '{cleaned_path}'")
        logger.info(f"Normalized path: '{normalized_path}'")
        
        # Try different path validation methods
        exists_os = os.path.exists(normalized_path)
        exists_pathlib = Path(normalized_path).exists()
        is_dir_os = os.path.isdir(normalized_path) if exists_os else False
        is_dir_pathlib = Path(normalized_path).is_dir() if exists_pathlib else False
        
        logger.info(f"Path validation results:")
        logger.info(f"  os.path.exists(): {exists_os}")
        logger.info(f"  pathlib.Path.exists(): {exists_pathlib}")
        logger.info(f"  os.path.isdir(): {is_dir_os}")
        logger.info(f"  pathlib.Path.is_dir(): {is_dir_pathlib}")
        
        # Validate folder path
        if not (exists_os or exists_pathlib):
            raise HTTPException(status_code=400, detail=f"Folder path does not exist: '{request.folder_path}' (normalized: '{normalized_path}')")
        
        if not (is_dir_os or is_dir_pathlib):
            raise HTTPException(status_code=400, detail=f"Path is not a directory: '{request.folder_path}' (normalized: '{normalized_path}')")
        
        # Use the normalized path for processing
        folder_path_to_use = normalized_path
        
        # Check if already processing
        global _processing_status
        if _processing_status['is_processing']:
            raise HTTPException(status_code=409, detail="Another folder is currently being processed")
        
        logger.info(f"Starting folder processing request for: '{folder_path_to_use}'")
        
        # Initialize slide processing service
        try:
            slide_service = get_slide_processing_service()
        except Exception as e:
            logger.error(f"Failed to initialize slide processing service: {e}")
            raise HTTPException(status_code=500, detail=f"Service initialization failed: {str(e)}")
        
        # Reset processing status
        _processing_status = {
            'is_processing': True,
            'current_file': '',
            'progress': 0.0,
            'files_processed': 0,
            'slides_processed': 0
        }
        
        # Process folder (this will take time, so we do it synchronously for now)
        # In production, you might want to make this truly async with a job queue
        result = slide_service.process_folder(
            folder_path=folder_path_to_use,
            progress_callback=update_progress
        )
        
        # Update final status
        _processing_status['is_processing'] = False
        
        if result['success']:
            logger.info(f"Successfully processed folder: {result}")
            return ProcessFolderResponse(
                success=True,
                message=result['message'],
                files_processed=result['files_processed'],
                slides_processed=result['slides_processed'],
                failed_files=result.get('failed_files', [])
            )
        else:
            logger.error(f"Folder processing failed: {result}")
            raise HTTPException(
                status_code=500, 
                detail=f"Processing failed: {result.get('error', 'Unknown error')}"
            )
            
    except HTTPException:
        _processing_status['is_processing'] = False
        raise
    except Exception as e:
        _processing_status['is_processing'] = False
        logger.error(f"Unexpected error processing folder: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/processing-status")
async def get_processing_status():
    """Get current processing status"""
    return _processing_status

@router.get("/stats")
async def get_slide_stats():
    """Get statistics about processed slides"""
    try:
        slide_service = get_slide_processing_service()
        stats = slide_service.get_processing_stats()
        return {
            "success": True,
            "stats": stats
        }
    except Exception as e:
        logger.error(f"Error getting slide stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/clear-all")
async def clear_all_slides():
    """Clear all processed slides from the vector database"""
    try:
        slide_service = get_slide_processing_service()
        success = slide_service.clear_all_slides()
        
        if success:
            return {"success": True, "message": "All slides cleared successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to clear slides")
            
    except Exception as e:
        logger.error(f"Error clearing slides: {e}")
        raise HTTPException(status_code=500, detail=str(e))
