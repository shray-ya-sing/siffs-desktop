import os
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
import base64
from PIL import Image
import mimetypes

logger = logging.getLogger(__name__)

class ImageProcessingService:
    """Service for processing standalone slide image files"""
    
    # Supported image formats for slide processing
    SUPPORTED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}
    
    def __init__(self):
        """Initialize the image processing service"""
        logger.info("🖼️ Initializing Image Processing Service...")
        
    def scan_folder_for_images(self, folder_path: str, fast_scan: bool = True, max_files: int = None) -> List[str]:
        """
        Scan folder and subdirectories for supported image files
        
        Args:
            folder_path: Path to the folder to scan
            fast_scan: If True, only check file extensions (much faster for large directories)
                      If False, verify each image file (slower but more accurate)
            max_files: Maximum number of files to return (None for unlimited)
            
        Returns:
            List of image file paths
        """
        try:
            logger.info(f"📁 Scanning folder for slide images: {folder_path}")
            if fast_scan:
                logger.info("⚡ Using fast scan (extension-based, no image validation)")
            else:
                logger.info("🔍 Using thorough scan (validating each image file)")
                
            image_files = []
            files_checked = 0
            
            # Walk through directory recursively
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    files_checked += 1
                    
                    # Progress logging for large directories
                    if files_checked % 1000 == 0:
                        logger.info(f"📁 Checked {files_checked} files, found {len(image_files)} images so far...")
                    
                    file_path = os.path.join(root, file)
                    file_ext = Path(file).suffix.lower()
                    
                    if file_ext in self.SUPPORTED_IMAGE_EXTENSIONS:
                        if fast_scan:
                            # Fast scan: just check extension and file exists
                            if os.path.isfile(file_path) and os.path.getsize(file_path) > 0:
                                image_files.append(file_path)
                        else:
                            # Thorough scan: verify it's actually a valid image file
                            if self._is_valid_image(file_path):
                                image_files.append(file_path)
                            else:
                                logger.warning(f"📁 Skipping invalid image file: {file_path}")
                    
                    # Stop if we've reached the maximum
                    if max_files and len(image_files) >= max_files:
                        logger.info(f"📁 Reached maximum file limit ({max_files}), stopping scan")
                        break
                
                if max_files and len(image_files) >= max_files:
                    break
            
            logger.info(f"📁 Scan completed: checked {files_checked} files, found {len(image_files)} valid image files")
            if image_files:
                logger.info("📁 Found image files:")
                for i, file in enumerate(image_files[:10], 1):  # Show first 10
                    logger.info(f"   {i}. {os.path.basename(file)}")
                if len(image_files) > 10:
                    logger.info(f"   ... and {len(image_files) - 10} more")
            else:
                logger.warning(f"📁 No valid image files found in {folder_path}")
            
            return image_files
            
        except Exception as e:
            logger.error(f"❌ Error scanning folder for images {folder_path}: {e}")
            return []
    
    def _is_valid_image(self, image_path: str) -> bool:
        """
        Check if file is a valid image
        
        Args:
            image_path: Path to the image file
            
        Returns:
            True if valid image, False otherwise
        """
        try:
            with Image.open(image_path) as img:
                # Try to load the image to verify it's valid
                img.verify()
            return True
        except Exception:
            return False
    
    def process_image_files(self, image_files: List[str]) -> List[Dict]:
        """
        Process a list of image files into slide data format
        
        Args:
            image_files: List of image file paths
            
        Returns:
            List of slide data dictionaries compatible with existing format
        """
        slides_data = []
        
        for i, image_path in enumerate(image_files):
            try:
                slide_data = self.process_single_image(image_path, slide_number=i + 1)
                if slide_data:
                    slides_data.append(slide_data)
                    
            except Exception as e:
                logger.error(f"❌ Error processing image {image_path}: {e}")
                continue
        
        logger.info(f"✅ Successfully processed {len(slides_data)} image files")
        return slides_data
    
    def process_single_image(self, image_path: str, slide_number: int = 1) -> Optional[Dict]:
        """
        Process a single image file into slide data format
        
        Args:
            image_path: Path to the image file
            slide_number: Slide number to assign
            
        Returns:
            Dictionary with slide data compatible with existing format
        """
        try:
            logger.debug(f"🖼️ Processing image: {image_path}")
            
            # Validate file exists
            if not os.path.exists(image_path):
                logger.error(f"❌ Image file not found: {image_path}")
                return None
            
            # Get file info
            file_path = os.path.abspath(image_path)
            file_name = os.path.basename(image_path)
            
            # Verify image is valid and get basic info
            try:
                with Image.open(image_path) as img:
                    width, height = img.size
                    format_name = img.format
                    logger.debug(f"🖼️ Image info: {width}x{height} {format_name}")
            except Exception as e:
                logger.error(f"❌ Invalid image file {image_path}: {e}")
                return None
            
            # Convert to base64 for embedding/storage
            image_base64 = self._image_to_base64(image_path)
            if not image_base64:
                logger.error(f"❌ Failed to convert image to base64: {image_path}")
                return None
            
            # Create slide data in the same format as PowerPoint slides
            slide_info = {
                'slide_number': slide_number,
                'image_path': file_path,  # Store original path
                'image_base64': image_base64,
                'file_path': file_path,
                'file_name': file_name,
                'source_type': 'image_file',  # Mark as direct image file
                'image_dimensions': {'width': width, 'height': height},
                'image_format': format_name
            }
            
            logger.debug(f"✅ Successfully processed image: {file_name}")
            return slide_info
            
        except Exception as e:
            logger.error(f"❌ Error processing image {image_path}: {e}")
            return None
    
    def _image_to_base64(self, image_path: str) -> str:
        """
        Convert image file to base64 string
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Base64 encoded string of the image
        """
        try:
            with open(image_path, 'rb') as image_file:
                image_data = image_file.read()
                base64_string = base64.b64encode(image_data).decode('utf-8')
                return base64_string
        except Exception as e:
            logger.error(f"❌ Error converting image to base64: {e}")
            return ""
    
    def get_supported_extensions(self) -> List[str]:
        """Get list of supported image file extensions"""
        return list(self.SUPPORTED_IMAGE_EXTENSIONS)
    
    def is_supported_image(self, file_path: str) -> bool:
        """
        Check if file is a supported image type
        
        Args:
            file_path: Path to the file
            
        Returns:
            True if supported image type, False otherwise
        """
        file_ext = Path(file_path).suffix.lower()
        return file_ext in self.SUPPORTED_IMAGE_EXTENSIONS
    
    def process_image_file(self, image_path: str, slide_number: int = 1) -> Optional[Dict]:
        """
        Alias for process_single_image for compatibility with slide processing service
        
        Args:
            image_path: Path to the image file
            slide_number: Slide number to assign
            
        Returns:
            Dictionary with slide data compatible with existing format
        """
        return self.process_single_image(image_path, slide_number)

# Global service instance
_image_service = None

def get_image_processing_service() -> ImageProcessingService:
    """Get or create global image processing service"""
    global _image_service
    if _image_service is None:
        _image_service = ImageProcessingService()
    return _image_service
