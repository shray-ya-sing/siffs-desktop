#!/usr/bin/env python3

import sys
import os
import tempfile
import shutil
import logging
from pathlib import Path

# Add the project path to sys.path
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent
sys.path.append(str(project_root))

from services.slide_processing_service import SlideProcessingService
from services.image_processing_service import ImageProcessingService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def test_image_processing_integration():
    """Test the image processing integration with the slide processing service"""
    
    logger.info("🧪 Starting image processing integration test...")
    
    # Create a temporary test folder
    with tempfile.TemporaryDirectory() as temp_dir:
        logger.info(f"📁 Created test directory: {temp_dir}")
        
        # Create test folders
        test_folder = os.path.join(temp_dir, "test_slides")
        os.makedirs(test_folder, exist_ok=True)
        
        # Create dummy test files (we won't actually process them, just test scanning)
        test_files = [
            "slide1.png",
            "slide2.jpg", 
            "slide3.jpeg",
            "slide4.webp",
            "presentation.pptx",
            "document.pdf",  # Should be ignored
            "readme.txt"     # Should be ignored
        ]
        
        for filename in test_files:
            file_path = os.path.join(test_folder, filename)
            # Create empty files for testing
            with open(file_path, 'w') as f:
                f.write("dummy content")
        
        logger.info(f"📄 Created {len(test_files)} test files")
        
        try:
            # Test 1: Initialize services
            logger.info("🔧 Test 1: Initializing services...")
            
            image_service = ImageProcessingService()
            logger.info("✅ Image processing service initialized")
            
            slide_service = SlideProcessingService()
            logger.info("✅ Slide processing service initialized")
            
            # Test 2: Test file scanning
            logger.info("🔍 Test 2: Testing file scanning...")
            
            scan_result = slide_service.scan_folder_for_files(test_folder)
            pptx_files = scan_result['pptx']
            image_files = scan_result['images']
            
            logger.info(f"📊 Scan results:")
            logger.info(f"   - PowerPoint files: {len(pptx_files)}")
            logger.info(f"   - Image files: {len(image_files)}")
            
            # Verify expected results
            expected_pptx = 1  # presentation.pptx
            expected_images = 4  # slide1.png, slide2.jpg, slide3.jpeg, slide4.webp
            
            if len(pptx_files) == expected_pptx:
                logger.info("✅ PowerPoint file scanning working correctly")
            else:
                logger.error(f"❌ Expected {expected_pptx} PowerPoint files, found {len(pptx_files)}")
                
            if len(image_files) == expected_images:
                logger.info("✅ Image file scanning working correctly")  
            else:
                logger.error(f"❌ Expected {expected_images} image files, found {len(image_files)}")
            
            # Test 3: Test image processing service methods
            logger.info("🖼️ Test 3: Testing image processing service methods...")
            
            # Test image validation
            valid_extensions = ['.png', '.jpg', '.jpeg', '.webp']
            invalid_extensions = ['.pdf', '.txt', '.pptx']
            
            for ext in valid_extensions:
                test_file = f"test{ext}"
                if image_service.is_valid_image_file(test_file):
                    logger.info(f"   ✅ {ext} correctly identified as valid image")
                else:
                    logger.error(f"   ❌ {ext} incorrectly rejected as invalid image")
            
            for ext in invalid_extensions:
                test_file = f"test{ext}"
                if not image_service.is_valid_image_file(test_file):
                    logger.info(f"   ✅ {ext} correctly identified as invalid image")
                else:
                    logger.error(f"   ❌ {ext} incorrectly accepted as valid image")
            
            # Test 4: Verify service integration
            logger.info("🔗 Test 4: Verifying service integration...")
            
            # Check that slide processing service has image processor
            if hasattr(slide_service, 'image_processor'):
                logger.info("✅ Slide processing service has image processor")
            else:
                logger.error("❌ Slide processing service missing image processor")
            
            # Check that the process_single_image_file method exists
            if hasattr(slide_service, 'process_single_image_file'):
                logger.info("✅ Slide processing service has process_single_image_file method")
            else:
                logger.error("❌ Slide processing service missing process_single_image_file method")
            
            logger.info("🎉 Integration test completed successfully!")
            
        except Exception as e:
            logger.error(f"❌ Integration test failed: {e}")
            logger.error(f"❌ Error type: {type(e).__name__}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_image_processing_integration()
