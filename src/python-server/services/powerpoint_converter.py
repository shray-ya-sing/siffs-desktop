# Siffs - Fast File Search Desktop Application
# Copyright (C) 2025  Siffs
# 
# Contact: github.suggest277@passinbox.com
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
import os
import tempfile
import logging
from typing import List, Dict, Tuple, Optional
from pathlib import Path
import win32com.client
from PIL import Image
import base64
from io import BytesIO

logger = logging.getLogger(__name__)

class PowerPointConverter:
    """Converts PowerPoint slides to images using COM automation"""
    
    def __init__(self):
        self.powerpoint = None
        self._initialize_powerpoint()
    
    def _initialize_powerpoint(self):
        """Initialize PowerPoint application via COM"""
        try:
            self.powerpoint = win32com.client.Dispatch("PowerPoint.Application")
            # Try to set invisible, but don't fail if it's not allowed
            try:
                self.powerpoint.Visible = False
            except:
                logger.warning("Could not set PowerPoint invisible, but continuing...")
            logger.info("PowerPoint COM application initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize PowerPoint COM: {e}")
            raise RuntimeError(f"PowerPoint not available: {e}")
    
    def convert_pptx_to_images(self, pptx_path: str, output_dir: str = None) -> List[Dict]:
        """
        Convert PowerPoint slides to images
        
        Args:
            pptx_path: Path to the PowerPoint file
            output_dir: Directory to save images (optional, uses temp if not provided)
            
        Returns:
            List of dictionaries containing slide data:
            [
                {
                    'slide_number': int,
                    'image_path': str,
                    'image_base64': str,
                    'file_path': str,
                    'file_name': str
                }
            ]
        """
        if not os.path.exists(pptx_path):
            raise FileNotFoundError(f"PowerPoint file not found: {pptx_path}")
        
        # Create output directory if not provided
        if output_dir is None:
            output_dir = tempfile.mkdtemp(prefix="pptx_slides_")
        else:
            os.makedirs(output_dir, exist_ok=True)
        
        presentation = None
        slide_data = []
        
        try:
            # Open the presentation
            presentation = self.powerpoint.Presentations.Open(pptx_path, ReadOnly=True, Untitled=True)
            logger.info(f"Opened presentation: {pptx_path} with {presentation.Slides.Count} slides")
            
            # Get file info
            file_path = os.path.abspath(pptx_path)
            file_name = os.path.basename(pptx_path)
            
            # Convert each slide to image
            for i in range(1, presentation.Slides.Count + 1):
                try:
                    slide = presentation.Slides(i)
                    
                    # Export slide as image
                    image_filename = f"slide_{i:03d}.png"
                    image_path = os.path.join(output_dir, image_filename)
                    
                    # Export slide to PNG format
                    # Parameters: filename, format, width, height
                    slide.Export(image_path, "PNG", 1920, 1080)  # High resolution export
                    
                    # Convert to base64 for storage
                    image_base64 = self._image_to_base64(image_path)
                    
                    slide_info = {
                        'slide_number': i,
                        'image_path': image_path,
                        'image_base64': image_base64,
                        'file_path': file_path,
                        'file_name': file_name
                    }
                    
                    slide_data.append(slide_info)
                    logger.info(f"Converted slide {i} from {file_name}")
                    
                except Exception as e:
                    logger.error(f"Error converting slide {i} from {pptx_path}: {e}")
                    continue
            
            logger.info(f"Successfully converted {len(slide_data)} slides from {file_name}")
            return slide_data
            
        except Exception as e:
            logger.error(f"Error processing PowerPoint file {pptx_path}: {e}")
            raise
        finally:
            # Clean up
            if presentation:
                try:
                    presentation.Close()
                except:
                    pass
    
    def _image_to_base64(self, image_path: str) -> str:
        """Convert image file to base64 string"""
        try:
            with open(image_path, 'rb') as image_file:
                image_data = image_file.read()
                base64_string = base64.b64encode(image_data).decode('utf-8')
                return base64_string
        except Exception as e:
            logger.error(f"Error converting image to base64: {e}")
            return ""
    
    def get_slide_image_data(self, image_path: str) -> bytes:
        """Get raw image data from file"""
        try:
            with open(image_path, 'rb') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error reading image data: {e}")
            return b""
    
    def cleanup_temp_images(self, output_dir: str):
        """Clean up temporary image files"""
        try:
            if os.path.exists(output_dir):
                import shutil
                shutil.rmtree(output_dir)
                logger.info(f"Cleaned up temporary directory: {output_dir}")
        except Exception as e:
            logger.error(f"Error cleaning up directory {output_dir}: {e}")
    
    def close(self):
        """Close PowerPoint application"""
        if self.powerpoint:
            try:
                self.powerpoint.Quit()
                self.powerpoint = None
                logger.info("PowerPoint application closed")
            except Exception as e:
                logger.error(f"Error closing PowerPoint: {e}")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

# Global converter instance
_converter_instance = None

def get_powerpoint_converter() -> PowerPointConverter:
    """Get or create global PowerPoint converter instance"""
    global _converter_instance
    if _converter_instance is None:
        _converter_instance = PowerPointConverter()
    return _converter_instance

def cleanup_powerpoint_converter():
    """Cleanup global converter instance"""
    global _converter_instance
    if _converter_instance:
        _converter_instance.close()
        _converter_instance = None
