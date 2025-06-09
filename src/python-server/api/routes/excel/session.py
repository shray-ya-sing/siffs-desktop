from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import StreamingResponse
from pathlib import Path
import sys
# Add the current directory to Python path
current_dir = Path(__file__).parent.parent.parent.parent.absolute()
sys.path.append(str(current_dir))
# Now import using relative path from python-server
from excel.session_management.excel_session_manager import ExcelSessionManager
import logging
# Get logger instance
logger = logging.getLogger(__name__)
import json

router = APIRouter(
    prefix="/api/excel/session",
    tags=["excel-session"],
)



@router.post("/start")
async def start_excel_session(request: dict):
    """Start a new Excel session for a file"""
    file_path = request.get("file_path")
    visible = request.get("visible", False)
    
    if not file_path:
        raise HTTPException(status_code=400, detail="file_path is required")
    
    try:
        session_manager = ExcelSessionManager()
        if not session_manager.open_session(file_path, visible=visible):
            raise HTTPException(status_code=500, detail="Failed to open workbook")
            
        return {"status": "success", "message": "Excel session started"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/end")
async def end_excel_session(request: dict):
    """End an Excel session for a file"""
    file_path = request.get("file_path")
    save = request.get("save", True)
    
    if not file_path:
        raise HTTPException(status_code=400, detail="file_path is required")
    
    try:
        session_manager = ExcelSessionManager()
        success = session_manager.close_session(file_path, save=save)
        
        if not success:
            raise HTTPException(status_code=404, detail="No active session found for file")
            
        return {"status": "success", "message": "Excel session ended"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/end-all")
async def end_all_excel_sessions(request: dict):
    """End an Excel session for a file and clean up all resources"""
    file_path = request.get("file_path")
    save = request.get("save", True)
    
    if not file_path:
        raise HTTPException(status_code=400, detail="file_path is required")
    
    try:
        session_manager = ExcelSessionManager()
        
        # First close the specific session
        success = session_manager.close_session(file_path, save=save)
        
        if not success:
            raise HTTPException(status_code=404, detail="No active session found for file")
            
        # Then close all sessions and clean up the singleton
        session_manager.close_all_sessions(save=save)
        
        # Clear the singleton instance
        ExcelSessionManager._instance = None
        
        return {
            "status": "success", 
            "message": "Excel session ended and resources cleaned up"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/save")
async def save_excel_session(request: dict):
    """Save an Excel session without closing it"""
    file_path = request.get("file_path")
    
    if not file_path:
        raise HTTPException(status_code=400, detail="file_path is required")
    
    try:
        session_manager = ExcelSessionManager()
        success = session_manager.save_session(file_path)
        
        if not success:
            raise HTTPException(status_code=404, detail="No active session found for file")
            
        return {"status": "success", "message": "Excel session saved"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
