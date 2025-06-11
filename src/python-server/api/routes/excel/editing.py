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
import logging
# Get logger instance
logger = logging.getLogger(__name__)
import json
import datetime
router = APIRouter(
    prefix="/api/excel",
    tags=["excel-editing"],
)

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
                success, request_edit_ids_by_sheet = writer.write_data_to_existing(metadata, file_path, version_id)
            
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
                "request_edit_ids_by_sheet": request_edit_ids_by_sheet,
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

