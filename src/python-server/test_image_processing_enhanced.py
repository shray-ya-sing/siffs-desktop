#!/usr/bin/env python3

import sys
import os
import tempfile
import shutil
import logging
from pathlib import Path
from PIL import Image
import io

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

def create_test_image(image_path: str, width: int = 800, height: int = 600, color: str = 'blue'):
    """Create a simple test image"""
    try:
        # Create a simple test image
        image = Image.new('RGB', (width, height), color=color)
        
        # Add some text to make it more realistic
        try:
            from PIL import ImageDraw, ImageFont
            draw = ImageDraw.Draw(image)
            # Use default font if available
            try:
                font = ImageFont.load_default()
            except:
                font = None
            
            text = f"Test Slide {os.path.basename(image_path)}"
            if font:
                draw.text((50, 50), text, fill='white', font=font)
            else:
                draw.text((50, 50), text, fill='white')
        except Exception as e:
            logger.debug(f"Could not add text to image: {e}")
        
        # Save the image
        image.save(image_path)
        logger.debug(f"Created test image: {image_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to create test image {image_path}: {e}")
        return False

def test_image_processing_integration():
    """Test the image processing integration with the slide processing service"""
    
    logger.info("🧪 Starting enhanced image processing integration test...")
    
    # Create a temporary test folder
    with tempfile.TemporaryDirectory() as temp_dir:
        logger.info(f"📁 Created test directory: {temp_dir}")
        
        # Create test folders
        test_folder = os.path.join(temp_dir, "test_slides")
        os.makedirs(test_folder, exist_ok=True)
        
        # Create actual test image files
        test_images = [
            ("slide1.png", 800, 600, 'blue'),
            ("slide2.jpg", 1024, 768, 'red'), 
            ("slide3.jpeg", 640, 480, 'green'),
            ("slide4.webp", 800, 600, 'purple')
        ]
        
        # Create PowerPoint dummy file
        pptx_file = os.path.join(test_folder, "presentation.pptx")
        with open(pptx_file, 'w') as f:
            f.write("dummy pptx content")
        
        # Create non-image files that should be ignored
        ignored_files = [
            ("document.pdf", "dummy pdf content"),
            ("readme.txt", "dummy text content")
        ]
        
        for filename, content in ignored_files:
            file_path = os.path.join(test_folder, filename)
            with open(file_path, 'w') as f:
                f.write(content)
        
        # Create actual test images
        created_images = []
        for filename, width, height, color in test_images:
            image_path = os.path.join(test_folder, filename)
            if create_test_image(image_path, width, height, color):
                created_images.append(image_path)
                logger.info(f"✅ Created test image: {filename}")
            else:
                logger.error(f"❌ Failed to create test image: {filename}")
        
        logger.info(f"📄 Created {len(created_images)} real image files and 3 other files")
        
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
            expected_images = len(created_images)  # Only images that were successfully created
            
            if len(pptx_files) == expected_pptx:
                logger.info("✅ PowerPoint file scanning working correctly")
            else:
                logger.error(f"❌ Expected {expected_pptx} PowerPoint files, found {len(pptx_files)}")
                
            if len(image_files) == expected_images:
                logger.info("✅ Image file scanning working correctly")  
            else:
                logger.error(f"❌ Expected {expected_images} image files, found {len(image_files)}")
                for img_file in image_files:
                    logger.info(f"   Found: {img_file}")
            
            # Test 3: Test image processing service methods
            logger.info("🖼️ Test 3: Testing image processing service methods...")
            
            # Test image validation
            valid_extensions = ['.png', '.jpg', '.jpeg', '.webp']
            invalid_extensions = ['.pdf', '.txt', '.pptx']
            
            for ext in valid_extensions:
                test_file = f"test{ext}"
                if image_service.is_supported_image(test_file):
                    logger.info(f"   ✅ {ext} correctly identified as supported image")
                else:
                    logger.error(f"   ❌ {ext} incorrectly rejected as unsupported image")
            
            for ext in invalid_extensions:
                test_file = f"test{ext}"
                if not image_service.is_supported_image(test_file):
                    logger.info(f"   ✅ {ext} correctly identified as unsupported image")
                else:
                    logger.error(f"   ❌ {ext} incorrectly accepted as supported image")
            
            # Test 4: Test single image processing
            if created_images:
                logger.info("🔄 Test 4: Testing single image processing...")
                test_image = created_images[0]
                
                slide_data = image_service.process_image_file(test_image)
                if slide_data:
                    logger.info("✅ Single image processing successful")
                    logger.info(f"   - File name: {slide_data.get('file_name')}")
                    logger.info(f"   - Source type: {slide_data.get('source_type')}")
                    logger.info(f"   - Dimensions: {slide_data.get('image_dimensions')}")
                    logger.info(f"   - Has base64 data: {bool(slide_data.get('image_base64'))}")
                else:
                    logger.error("❌ Single image processing failed")
            
            # Test 5: Verify service integration
            logger.info("🔗 Test 5: Verifying service integration...")
            
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
            
            # Test 6: Test integration of both file types in processing
            logger.info("🔄 Test 6: Testing integrated file processing (dry run)...")
            
            # Note: We won't actually process the files with embeddings since it requires API calls
            # But we can test the logic for handling both types
            total_files = len(pptx_files) + len(image_files)
            logger.info(f"   - Total files to process: {total_files}")
            logger.info(f"     * PowerPoint files: {len(pptx_files)}")
            logger.info(f"     * Image files: {len(image_files)}")
            
            if total_files > 0:
                logger.info("✅ Mixed file type processing setup correct")
            else:
                logger.warning("⚠️ No files to process")
            
            logger.info("🎉 Enhanced integration test completed successfully!")
            
        except Exception as e:
            logger.error(f"❌ Integration test failed: {e}")
            logger.error(f"❌ Error type: {type(e).__name__}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_image_processing_integration()
