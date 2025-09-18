#!/usr/bin/env python3

import sys
import os
import tempfile
import logging
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# Add the project path to sys.path
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent
sys.path.append(str(project_root))

from services.slide_processing_service import SlideProcessingService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def create_test_slide_image(image_path: str, slide_content: str, width: int = 800, height: int = 600):
    """Create a test slide image with specific content"""
    try:
        # Create image with white background
        image = Image.new('RGB', (width, height), color='white')
        draw = ImageDraw.Draw(image)
        
        # Try to use default font
        try:
            font = ImageFont.load_default()
        except:
            font = None
        
        # Draw title and content
        title = f"Test Slide: {os.path.splitext(os.path.basename(image_path))[0]}"
        draw.text((50, 50), title, fill='black', font=font)
        draw.text((50, 150), slide_content, fill='darkblue', font=font)
        
        # Add some visual elements
        draw.rectangle([50, 300, width-50, 350], fill='lightblue')
        draw.text((60, 315), "Key Point: " + slide_content[:50], fill='white', font=font)
        
        # Save the image
        image.save(image_path)
        logger.info(f"✅ Created test slide: {os.path.basename(image_path)}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to create test slide {image_path}: {e}")
        return False

def test_end_to_end_image_processing():
    """Test complete end-to-end image processing including embedding creation"""
    
    logger.info("🧪 Starting end-to-end image processing test...")
    
    # Create test images with different content
    test_slides = [
        ("data_analysis.png", "Data analysis techniques using Python pandas and visualization"),
        ("machine_learning.jpg", "Machine learning algorithms and neural networks overview"),
        ("project_planning.png", "Project planning methodologies and agile development"),
    ]
    
    # Create a temporary test folder
    with tempfile.TemporaryDirectory() as temp_dir:
        logger.info(f"📁 Created test directory: {temp_dir}")
        
        # Create test folder
        test_folder = os.path.join(temp_dir, "test_slides")
        os.makedirs(test_folder, exist_ok=True)
        
        # Create test slide images
        created_images = []
        for filename, content in test_slides:
            image_path = os.path.join(test_folder, filename)
            if create_test_slide_image(image_path, content):
                created_images.append((image_path, content))
        
        if not created_images:
            logger.error("❌ No test images were created successfully")
            return
        
        logger.info(f"📄 Created {len(created_images)} test slide images")
        
        try:
            # Initialize the slide processing service
            logger.info("🔧 Initializing slide processing service...")
            slide_service = SlideProcessingService()
            logger.info("✅ Slide processing service initialized")
            
            # Test processing individual image files
            logger.info("🖼️ Testing individual image file processing...")
            
            for image_path, expected_content in created_images:
                logger.info(f"🔄 Processing image: {os.path.basename(image_path)}")
                
                try:
                    result = slide_service.process_single_image_file(image_path)
                    
                    if result['success']:
                        logger.info(f"✅ Successfully processed {os.path.basename(image_path)}")
                        logger.info(f"   - Slides processed: {result['slides_processed']}")
                        logger.info(f"   - Embeddings created: {result['embeddings_created']}")
                    else:
                        logger.error(f"❌ Failed to process {os.path.basename(image_path)}: {result.get('error')}")
                        
                except Exception as e:
                    logger.error(f"❌ Exception processing {os.path.basename(image_path)}: {e}")
                    continue
            
            # Test searching for the processed images
            logger.info("🔍 Testing search functionality...")
            
            search_queries = [
                "data analysis Python",
                "machine learning neural networks",
                "project planning agile"
            ]
            
            for query in search_queries:
                logger.info(f"🔎 Searching for: '{query}'")
                
                try:
                    results = slide_service.search_slides(query, top_k=3)
                    
                    if results:
                        logger.info(f"✅ Found {len(results)} results for '{query}'")
                        for i, result in enumerate(results, 1):
                            score = result.get('score', 0.0)
                            file_name = result.get('file_name', 'unknown')
                            logger.info(f"   {i}. {file_name} (score: {score:.4f})")
                    else:
                        logger.warning(f"⚠️ No results found for '{query}'")
                        
                except Exception as e:
                    logger.error(f"❌ Error searching for '{query}': {e}")
                    continue
            
            # Test folder processing (should handle mixed files)
            logger.info("📁 Testing folder processing...")
            
            try:
                # Process the entire folder (contains only images in this case)
                result = slide_service.process_folder(test_folder)
                
                if result['success']:
                    logger.info("✅ Folder processing successful")
                    logger.info(f"   - Files processed: {result['files_processed']}")
                    logger.info(f"   - Total slides processed: {result['slides_processed']}")
                    if result.get('failed_files'):
                        logger.warning(f"   - Failed files: {len(result['failed_files'])}")
                else:
                    logger.error(f"❌ Folder processing failed: {result.get('error')}")
                    
            except Exception as e:
                logger.error(f"❌ Exception during folder processing: {e}")
            
            # Get processing stats
            logger.info("📊 Getting processing statistics...")
            
            try:
                stats = slide_service.get_processing_stats()
                logger.info(f"📊 Processing Statistics:")
                logger.info(f"   - Total slides in database: {stats.get('total_slides', 0)}")
                logger.info(f"   - Index dimension: {stats.get('index_dimension', 0)}")
                logger.info(f"   - Index fullness: {stats.get('index_fullness', 0.0):.2%}")
                
            except Exception as e:
                logger.error(f"❌ Error getting processing stats: {e}")
            
            logger.info("🎉 End-to-end image processing test completed!")
            
        except Exception as e:
            logger.error(f"❌ End-to-end test failed: {e}")
            logger.error(f"❌ Error type: {type(e).__name__}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_end_to_end_image_processing()
