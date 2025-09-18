#!/usr/bin/env python3
"""
Test script to verify all services work correctly
"""
import os
import sys
import logging
from pathlib import Path

# Add current directory to Python path
current_dir = Path(__file__).parent.absolute()
sys.path.append(str(current_dir))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_imports():
    """Test that all modules can be imported"""
    try:
        logger.info("Testing imports...")
        
        # Test WIN32COM import
        import win32com.client
        logger.info("✅ win32com.client import successful")
        
        # Test VoyageAI import
        import voyageai
        logger.info("✅ voyageai import successful")
        
        # Test Pinecone import
        from pinecone import Pinecone
        logger.info("✅ pinecone import successful")
        
        # Test our service imports
        from services.powerpoint_converter import PowerPointConverter
        logger.info("✅ PowerPointConverter import successful")
        
        from services.voyage_embeddings import VoyageEmbeddingsService
        logger.info("✅ VoyageEmbeddingsService import successful")
        
        from services.pinecone_db import PineconeVectorDB
        logger.info("✅ PineconeVectorDB import successful")
        
        from services.slide_processing_service import SlideProcessingService
        logger.info("✅ SlideProcessingService import successful")
        
        # Test FastAPI route import
        from api.routes.slides import router
        logger.info("✅ Slides router import successful")
        
        # Test main app import
        from app import app
        logger.info("✅ Main app import successful")
        
        logger.info("✅ All imports successful!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Import failed: {e}")
        return False

def test_environment():
    """Test environment variables"""
    logger.info("Testing environment variables...")
    
    # Load environment variables
    from dotenv import load_dotenv
    project_root = Path(__file__).parent.parent.parent.absolute()
    env_path = project_root / '.env'
    load_dotenv(env_path)
    
    voyage_key = os.getenv('VOYAGE_API_KEY')
    pinecone_key = os.getenv('PINECONE_API_KEY')
    
    if voyage_key and voyage_key != 'your_voyage_api_key_here':
        logger.info("✅ VOYAGE_API_KEY found")
    else:
        logger.warning("⚠️ VOYAGE_API_KEY not set or still default value")
    
    if pinecone_key and pinecone_key != 'your_pinecone_api_key_here':
        logger.info("✅ PINECONE_API_KEY found")
    else:
        logger.warning("⚠️ PINECONE_API_KEY not set or still default value")

def test_powerpoint_com():
    """Test PowerPoint COM initialization"""
    try:
        logger.info("Testing PowerPoint COM initialization...")
        import win32com.client
        
        # Try to create PowerPoint application
        ppt = win32com.client.Dispatch("PowerPoint.Application")
        ppt.Visible = False
        logger.info("✅ PowerPoint COM application created successfully")
        
        # Clean up
        ppt.Quit()
        logger.info("✅ PowerPoint COM application closed successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ PowerPoint COM test failed: {e}")
        logger.info("💡 Make sure Microsoft PowerPoint is installed")
        return False

if __name__ == "__main__":
    logger.info("🚀 Starting Siffs services test...")
    
    success = True
    
    # Test imports
    if not test_imports():
        success = False
    
    # Test environment
    test_environment()
    
    # Test PowerPoint COM (this might fail if PowerPoint is not installed)
    test_powerpoint_com()
    
    if success:
        logger.info("🎉 All core tests passed! The indexing system should work correctly.")
        logger.info("📝 To start the server, run: python app.py")
    else:
        logger.error("❌ Some tests failed. Please fix the issues before proceeding.")
        sys.exit(1)
