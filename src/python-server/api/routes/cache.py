from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
import logging

# Get logger instance
logger = logging.getLogger(__name__)

router = APIRouter(tags=["cache"])

@router.post("/clear-cache")
async def clear_cache_endpoint():
    """API endpoint to clear metadata cache"""
    import sys
    from pathlib import Path
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
