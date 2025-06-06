from fastapi import APIRouter
import logging
# Get logger instance
logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])

#------------------------------------ TEST ENDPOINTS---------------------------------------------
# Simple health check endpoint
@router.get("/api/health")
async def health_check():
    return {"status": "ok", "message": "Python server is running"}

# Example API endpoint
@router.get("/api/example")
async def example_endpoint():
    return {"message": "Hello from FastAPI server!"}

@router.get("/api/test-logging")
async def test_logging():
    # Test logging at different levels
    logger.debug("This is a DEBUG message")
    logger.info("This is an INFO message")
    logger.warning("This is a WARNING message")
    logger.error("This is an ERROR message")
    return {"message": "Logging test complete"}