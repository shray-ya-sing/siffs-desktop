from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import StreamingResponse
from pathlib import Path
import sys
# Add the current directory to Python path
current_dir = Path(__file__).parent.parent.parent.parent.absolute()
sys.path.append(str(current_dir))
# Now import using relative path from python-server
from api.models.excel import AnalyzeMetadataRequest
from excel.editing.excel_writer import ExcelWriter
from excel.editing.approval.excel_pending_edit_manager import ExcelPendingEditManager
from excel.session_management.excel_session_manager import ExcelSessionManager
import logging
# Get logger instance
logger = logging.getLogger(__name__)
import json
import datetime
from typing import Dict, List, Any, Tuple, Union
router = APIRouter(
    prefix="/api/excel",
    tags=["excel-editing"],
)

def get_session_manager() -> ExcelSessionManager:
    """Dependency to get the shared session manager instance."""
    return ExcelSessionManager()

#------------------------------------ MODEL CREATE OR EDIT---------------------------------------------
# Endpoint to edit Excel file with metadata
@router.post("/edit-excel")
async def edit_excel(request: dict):
    """
    Edit an EXISTING Excel file using the provided metadata.
    
    Request body:
    {
        "file_path": "/path/to/excel.xlsx",
        "metadata": {
            "Sheet1": [
                {
                    "cell": "A1",
                    "formula": "Test",
                    "font_style": "Arial",
                    "font_size": 12,
                    "bold": true,
                    "text_color": "#FF0000",
                    "horizontal_alignment": "center",
                    "vertical_alignment": "center",
                    "number_format": "0.00",
                    "fill_color": "#FFFF00",
                    "wrap_text": true
                }
            ]
        },
        "visible": false  # Optional, whether to show Excel during editing
        "version_id": int  # Optional, version ID for tracking edits
    }
    """
    logger.info("Received request to edit Excel file")
    
    try:
        # Extract and validate request data
        file_path = request.get("file_path")
        metadata = request.get("metadata")
        visible = request.get("visible", True)
        version_id = request.get("version_id")
        logger.info(f"Extracted {file_path}, {metadata}, {visible}, {version_id}")
        
        if not file_path or not isinstance(file_path, str):
            raise HTTPException(
                status_code=400,
                detail="Valid file_path is required"
            )
            
        if not metadata or not isinstance(metadata, dict):
            raise HTTPException(
                status_code=400,
                detail="Metadata must be a non-empty dictionary"
            )

        try:
            logger.info(f"Using ExcelWriter instance to write to workbook")
            # Use the singleton instance to write data to existing workbook
            with ExcelWriter(visible=visible) as writer:
                success, request_pending_edits = writer.write_data_to_existing(metadata, file_path, version_id)
            
            if not success:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to write data to Excel"
                )
            logger.info(f"Successfully updated {file_path} and retrieved edit ids")
            return {
                "status": "success",
                "message": f"Successfully updated {file_path}",
                "file_path": file_path,
                "modified_sheets": list(metadata.keys()),
                "request_pending_edits": request_pending_edits,
                "timestamp": datetime.datetime.now().isoformat()
            }
            
        except PermissionError as pe:
            logger.error(f"Permission error writing to {file_path}: {str(pe)}")
            raise HTTPException(
                status_code=403,
                detail=f"Permission denied when writing to {file_path}"
            )
            
        except Exception as e:
            logger.error(f"Error writing to Excel file: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Error writing to Excel file: {str(e)}"
            )
            
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
        
    except Exception as e:
        # Log the full error for debugging
        logger.error(f"Unexpected error editing Excel: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Internal server error",
                "message": "An unexpected error occurred while editing the Excel file"
            }
        )
        


@router.post("/create-excel")
async def create_excel(request: dict):
    """
    Create a new Excel file using the provided metadata.
    
    Request body:
    {
        "file_path": "/path/to/excel.xlsx",
        "metadata": {
            "Sheet1": [
                {
                    "cell": "A1",
                    "formula": "Test",
                    "font_style": "Arial",
                    "font_size": 12,
                    "bold": true,
                    "text_color": "#FF0000",
                    "horizontal_alignment": "center",
                    "vertical_alignment": "center",
                    "number_format": "0.00",
                    "fill_color": "#FFFF00",
                    "wrap_text": true
                }
            ]
        },
        "visible": false  # Optional, whether to show Excel during editing
        "version_id": 1  # Optional, version ID for tracking edits
    }
    """
    logger.info("Received request to edit Excel file")
    
    try:
        # Extract and validate request data
        file_path = request.get("file_path")
        metadata = request.get("metadata")
        visible = request.get("visible", False)
        version_id = request.get("version_id", 1)
        
        if not file_path or not isinstance(file_path, str):
            raise HTTPException(
                status_code=400,
                detail="Valid file_path is required"
            )
            
        if not metadata or not isinstance(metadata, dict):
            raise HTTPException(
                status_code=400,
                detail="Metadata must be a non-empty dictionary"
            )

        try:
            with ExcelWriter(visible=visible) as writer:
                # Use the singleton instance to write data to existing workbook
                success, request_edit_ids_by_sheet = writer.write_data_to_new(metadata, file_path, version_id)
            if not success:
                logger.error("Failed to write data to Excel")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to write data to Excel"
                )
            
            return {
                "status": "success",
                "message": f"Successfully created new excel at {file_path}",
                "file_path": file_path,
                "modified_sheets": list(metadata.keys()),
                "request_edit_ids_by_sheet": request_edit_ids_by_sheet
            }
            
        except PermissionError as pe:
            logger.error(f"Permission error writing to {file_path}: {str(pe)}")
            raise HTTPException(
                status_code=403,
                detail=f"Permission denied when writing to {file_path}"
            )
            
        except Exception as e:
            logger.error(f"Error writing to Excel file: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Error writing to Excel file: {str(e)}"
            )
            
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
        
    except Exception as e:
        # Log the full error for debugging
        logger.error(f"Unexpected error editing Excel: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Internal server error",
                "message": "An unexpected error occurred while editing the Excel file"
            }
        )



#------------------------------------ EDIT ACCEPTANCE & REJECTION ---------------------------------------------

@router.post("/edits/accept", response_model=Dict[str, Any])
async def accept_edits(
    request: dict,
    ) -> Dict[str, Any]:
    """
    Accept multiple pending edits by their IDs.
    
    Args:
        edit_ids: List of edit IDs to accept
        
    Returns:
        Dictionary containing:
        - success: Whether the operation completed successfully
        - accepted_count: Number of edits successfully accepted
        - failed_ids: List of edit IDs that failed to be accepted
        - accepted_edit_version_ids: The version IDs that were updated
    """
    try:
        if not request.get('edit_ids'):
            raise HTTPException(status_code=400, detail="No edit IDs provided")
        
        with ExcelPendingEditManager() as edit_manager:

            result = edit_manager.accept_edits(
                edit_ids=request.get('edit_ids')
            )
            
        if not result.get('success', False):
            logger.exception(f"Error accepting edits: {str(result.get('error', 'Unknown error'))}")
            raise HTTPException(status_code=500, detail=f"Failed to accept edits: {str(result.get('error', 'Unknown error'))}")
                
        return result
        
    except Exception as e:
        logger.exception(f"Error accepting edits: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to accept edits: {str(e)}")

@router.post("/edits/reject", response_model=Dict[str, Any])
async def reject_edits(
    request: dict,
) -> Dict[str, Any]:
        """
        Reject multiple pending edits by their IDs, restoring original cell states.
        
        Args:
            edit_ids: List of edit IDs to reject
            
        Returns:
            Dictionary containing:
            - success: Whether the operation completed successfully
            - rejected_count: Number of edits successfully rejected
            - failed_ids: List of edit IDs that failed to be rejected
        """
        try:
            if not request.get('edit_ids'):
                raise HTTPException(status_code=400, detail="No edit IDs provided")
            
            with ExcelPendingEditManager() as edit_manager:
                result = edit_manager.reject_edits(
                    edit_ids=request.get('edit_ids')
                )
                
            if not result.get('success', False):
                error_msg = str(result.get('error', 'Unknown error'))
                logger.error(f"Error rejecting edits: {error_msg}")
                raise HTTPException(
                    status_code=500, 
                    detail=f"Failed to reject edits: {error_msg}"
                )
                
            return result
            
        except Exception as e:
            error_msg = str(e)
            logger.exception(f"Error in reject_edits endpoint: {error_msg}")
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to process reject request: {error_msg}"
            )