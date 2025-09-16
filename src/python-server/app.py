import os
import sys
import logging
from pathlib import Path
# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Get the project root directory (where .env is located)
project_root = Path(__file__).parent.parent.parent.absolute()

# Load environment variables from the .env file in the root
env_path = project_root / '.env'
logger.info(f"Loading environment variables from: {env_path}")
logger.info(f".env file exists: {env_path.exists()}")

load_dotenv(env_path)

# Debug: Check if environment variables are loaded
logger.info("Environment variables loaded:")
logger.info(f"  PROJECT_ROOT: {project_root}")
logger.info(f"  ENV_PATH: {env_path}")
logger.info(f"  PINECONE_API_KEY: {'SET' if os.getenv('PINECONE_API_KEY') else 'NOT SET'}")
logger.info(f"  VOYAGE_API_KEY: {'SET' if os.getenv('VOYAGE_API_KEY') else 'NOT SET'}")
logger.info(f"  NODE_ENV: {os.getenv('NODE_ENV', 'not set')}")

if os.getenv('PINECONE_API_KEY'):
    logger.info(f"  PINECONE_API_KEY length: {len(os.getenv('PINECONE_API_KEY'))}")
if os.getenv('VOYAGE_API_KEY'):
    logger.info(f"  VOYAGE_API_KEY length: {len(os.getenv('VOYAGE_API_KEY'))}")

# Add the current directory to Python path
current_dir = Path(__file__).parent.absolute()
sys.path.append(str(current_dir))

# Import routers
from api.routes.slides import router as slides_router

# Create FastAPI app
app = FastAPI(title="Siffs API")

# Include routers
app.include_router(slides_router, prefix="/api")

@app.on_event("startup")
async def startup_event():
    logger.info("Siffs API starting up...")
    
    # Print all registered routes
    for route in app.routes:
        if hasattr(route, 'methods'):
            logger.info(f"HTTP {list(route.methods)} {route.path}")
    
    logger.info("Siffs API startup completed")
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred"}
    )
# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"{request.method} {request.url.path}")
    
    try:
        response = await call_next(request)
        logger.info(f"{request.method} {request.url.path} - {response.status_code}")
        return response
    except Exception as e:
        logger.error(f"Error processing {request.method} {request.url.path}: {str(e)}")
        raise
if __name__ == '__main__':
    import uvicorn
    port = int(os.environ.get('PORT', 3001))
    logger.info(f"Starting Siffs API server on port {port}")
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=True)
