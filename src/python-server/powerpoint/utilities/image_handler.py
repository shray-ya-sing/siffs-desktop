import os
import json
import requests
import hashlib
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import tempfile
import shutil
from urllib.parse import urlparse
import mimetypes

logger = logging.getLogger(__name__)

class PowerPointImageHandler:
    """Handles image operations for PowerPoint integration including URL downloads and attachment processing."""
    
    def __init__(self, cache_dir: Optional[str] = None):
        """Initialize the image handler with optional cache directory."""
        self.cache_dir = Path(cache_dir) if cache_dir else Path(tempfile.gettempdir()) / "ppt_images"
        self.cache_dir.mkdir(exist_ok=True)
        self.supported_formats = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'}
        
    def load_logo_database(self, json_file_path: str, base_url: str = "https://logodb.com") -> Dict[str, Dict[str, Any]]:
        """Load the logo database from JSON file.
        
        Args:
            json_file_path: Path to JSON file containing company logo data
            base_url: Base URL for logo images (default: https://logodb.com)
            
        Returns:
            Dictionary mapping company names to logo data with full URLs
        """
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)
            
            processed_data = {}
            for company_data in raw_data:
                company_name = company_data.get('name', '')
                if not company_name:
                    continue
                
                # Extract logo URLs from the nested structure
                png_data = company_data.get('png', {}).get('icon', {})
                logo_info = {
                    'symbol': company_data.get('symbol', ''),
                    'website_domain': company_data.get('website_domain', ''),
                    'country': company_data.get('country', ''),
                    'urls': {}
                }
                
                # Process bright background logos
                bright_bg = png_data.get('for_bright_background', {})
                for size, path in bright_bg.items():
                    full_url = base_url + path if path.startswith('/') else path
                    logo_info['urls'][f'bright_{size}'] = full_url
                
                # Process dark background logos if available
                dark_bg = png_data.get('for_dark_background', {})
                for size, path in dark_bg.items():
                    full_url = base_url + path if path.startswith('/') else path
                    logo_info['urls'][f'dark_{size}'] = full_url
                
                processed_data[company_name] = logo_info
                
                # Also add entries for symbol and alternative names for better matching
                symbol = company_data.get('symbol', '')
                if symbol and symbol != company_name:
                    processed_data[symbol] = logo_info
                
            logger.info(f"Loaded {len(processed_data)} companies from logo database")
            return processed_data
            
        except Exception as e:
            logger.error(f"Failed to load logo database: {e}")
            return {}
    
    def download_image_from_url(self, url: str, filename: Optional[str] = None) -> Optional[str]:
        """Download image from URL and save to cache directory.
        
        Args:
            url: URL of the image to download
            filename: Optional custom filename, otherwise generated from URL
            
        Returns:
            Path to downloaded image file or None if failed
        """
        try:
            # Create filename if not provided
            if not filename:
                url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
                parsed_url = urlparse(url)
                ext = Path(parsed_url.path).suffix.lower()
                if not ext or ext not in self.supported_formats:
                    ext = '.png'  # Default extension
                filename = f"image_{url_hash}{ext}"
            
            file_path = self.cache_dir / filename
            
            # Check if already downloaded
            if file_path.exists():
                logger.info(f"Image already cached: {file_path}")
                return str(file_path)
            
            # Download the image
            logger.info(f"Downloading image from: {url}")
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=30, stream=True)
            response.raise_for_status()
            
            # Verify content type
            content_type = response.headers.get('content-type', '').lower()
            if not any(img_type in content_type for img_type in ['image/', 'application/octet-stream']):
                logger.warning(f"Unexpected content type: {content_type}")
            
            # Save the image
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            logger.info(f"Image downloaded successfully: {file_path}")
            return str(file_path)
            
        except Exception as e:
            logger.error(f"Failed to download image from {url}: {e}")
            return None
    
    def process_attachment_image(self, attachment_data: bytes, filename: str) -> Optional[str]:
        """Process an attached image file.
        
        Args:
            attachment_data: Raw bytes of the image file
            filename: Original filename of the attachment
            
        Returns:
            Path to processed image file or None if failed
        """
        try:
            # Validate file extension
            file_ext = Path(filename).suffix.lower()
            if file_ext not in self.supported_formats:
                logger.error(f"Unsupported image format: {file_ext}")
                return None
            
            # Create unique filename
            file_hash = hashlib.md5(attachment_data).hexdigest()[:8]
            safe_filename = f"attachment_{file_hash}_{Path(filename).name}"
            file_path = self.cache_dir / safe_filename
            
            # Save the attachment
            with open(file_path, 'wb') as f:
                f.write(attachment_data)
            
            logger.info(f"Attachment processed successfully: {file_path}")
            return str(file_path)
            
        except Exception as e:
            logger.error(f"Failed to process attachment {filename}: {e}")
            return None
    
    def find_company_logos(self, company_names: List[str], logo_database: Dict[str, Dict[str, Any]], 
                          prefer_size: str = "64", prefer_background: str = "bright") -> Dict[str, str]:
        """Find logo URLs for given company names.
        
        Args:
            company_names: List of company names to find logos for
            logo_database: Dictionary mapping company names to logo data
            prefer_size: Preferred logo size ("32" or "64")
            prefer_background: Preferred background type ("bright" or "dark")
            
        Returns:
            Dictionary mapping company names to their best logo URLs
        """
        found_logos = {}
        
        for company in company_names:
            best_url = None
            matched_company = None
            
            # Try exact match first
            if company in logo_database:
                matched_company = company
            else:
                # Try case-insensitive match
                company_lower = company.lower()
                for db_company in logo_database.keys():
                    if db_company.lower() == company_lower:
                        matched_company = db_company
                        break
                
                # Try partial match
                if not matched_company:
                    for db_company in logo_database.keys():
                        if company_lower in db_company.lower() or db_company.lower() in company_lower:
                            matched_company = db_company
                            logger.info(f"Partial match found: '{company}' -> '{db_company}'")
                            break
            
            if matched_company:
                logo_data = logo_database[matched_company]
                urls = logo_data.get('urls', {})
                
                # Find the best URL based on preferences
                # Priority: preferred background + preferred size, then fallback options
                preferred_key = f"{prefer_background}_{prefer_size}"
                if preferred_key in urls:
                    best_url = urls[preferred_key]
                else:
                    # Fallback to other sizes with same background
                    for size in ["64", "32"]:
                        key = f"{prefer_background}_{size}"
                        if key in urls:
                            best_url = urls[key]
                            break
                    
                    # If still no match, try other background type
                    if not best_url:
                        other_bg = "dark" if prefer_background == "bright" else "bright"
                        for size in ["64", "32"]:
                            key = f"{other_bg}_{size}"
                            if key in urls:
                                best_url = urls[key]
                                break
                
                if best_url:
                    found_logos[company] = best_url
                    logger.info(f"Found logo for '{company}': {best_url}")
                else:
                    logger.warning(f"No valid logo URL found for company: {company}")
            else:
                logger.warning(f"No logo found for company: {company}")
        
        return found_logos
    
    def download_company_logos(self, company_logos: Dict[str, str]) -> Dict[str, str]:
        """Download logos for companies and return mapping of company names to local file paths.
        
        Args:
            company_logos: Dictionary mapping company names to logo URLs
            
        Returns:
            Dictionary mapping company names to local file paths
        """
        downloaded_logos = {}
        
        for company, url in company_logos.items():
            # Create filename based on company name
            safe_company_name = "".join(c for c in company if c.isalnum() or c in (' ', '-', '_')).strip()
            safe_company_name = safe_company_name.replace(' ', '_')
            
            file_path = self.download_image_from_url(url, f"logo_{safe_company_name}.png")
            if file_path:
                downloaded_logos[company] = file_path
            else:
                logger.error(f"Failed to download logo for {company}")
        
        return downloaded_logos
    
    def process_company_names_for_logos(self, company_names: List[str], logo_db_path: str, 
                                      prefer_size: str = "64", prefer_background: str = "bright") -> Dict[str, str]:
        """Process company names and download their logos in one step.
        
        Args:
            company_names: List of company names to find logos for
            logo_db_path: Path to the logo database JSON file
            prefer_size: Preferred logo size ("32" or "64")
            prefer_background: Preferred background type ("bright" or "dark")
            
        Returns:
            Dictionary mapping company names to local file paths of downloaded logos
        """
        # Load the logo database
        logo_database = self.load_logo_database(logo_db_path)
        if not logo_database:
            logger.error("Failed to load logo database")
            return {}
        
        # Find logo URLs for companies
        company_logo_urls = self.find_company_logos(company_names, logo_database, prefer_size, prefer_background)
        if not company_logo_urls:
            logger.info("No logos found for any companies")
            return {}
        
        # Download the logos
        downloaded_logos = self.download_company_logos(company_logo_urls)
        logger.info(f"Successfully downloaded {len(downloaded_logos)} company logos")
        
        return downloaded_logos
    
    def generate_image_metadata(self, image_path: str, position: Dict[str, float], 
                              shape_name: str) -> Dict[str, Any]:
        """Generate metadata for adding an image to PowerPoint.
        
        Args:
            image_path: Path to the image file
            position: Dictionary with left, top, width, height positions
            shape_name: Name for the image shape
            
        Returns:
            Dictionary containing image metadata for PowerPoint
        """
        return {
            "shape_type": "picture",
            "image_path": image_path,
            "left": position.get("left", 100),
            "top": position.get("top", 100),
            "width": position.get("width", 100),
            "height": position.get("height", 100),
            "name": shape_name
        }
    
    def cleanup_cache(self, max_age_hours: int = 24):
        """Clean up old files from the cache directory.
        
        Args:
            max_age_hours: Maximum age of files to keep in hours
        """
        try:
            import time
            current_time = time.time()
            max_age_seconds = max_age_hours * 3600
            
            for file_path in self.cache_dir.glob("*"):
                if file_path.is_file():
                    file_age = current_time - file_path.stat().st_mtime
                    if file_age > max_age_seconds:
                        file_path.unlink()
                        logger.debug(f"Cleaned up old cache file: {file_path}")
                        
        except Exception as e:
            logger.error(f"Error during cache cleanup: {e}")
