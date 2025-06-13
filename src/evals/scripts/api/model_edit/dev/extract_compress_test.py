import requests
import time
import logging
from typing import Dict, Any, Optional
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('extract_compress_test.log')
    ]
)
logger = logging.getLogger(__name__)

# Configuration
BASE_URL = "http://127.0.0.1:3001/api"
TEST_FILE = r"C:\Users\shrey\OneDrive\Desktop\docs\test\single_tab_no_error.xlsx"
EXTRACT_ENDPOINT = "/excel/extract-metadata-chunks"
COMPRESS_ENDPOINT = "/excel/compress-chunks"

def make_request(method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
    """Helper function to make HTTP requests with error handling and logging"""
    url = f"{BASE_URL}{endpoint}"
    logger.info(f"Making {method} request to {url}")
    
    try:
        if method.upper() == "GET":
            response = requests.get(url, params=data)
        elif method.upper() == "POST":
            logger.debug(f"Request data: {data}")
            response = requests.post(url, json=data)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
        
        response.raise_for_status()
        logger.info("Request successful")
        return response.json()
    except requests.exceptions.RequestException as e:
        error_msg = f"Request failed: {str(e)}"
        if hasattr(e, 'response') and e.response is not None:
            error_msg += f" | Status: {e.response.status_code} | Response: {e.response.text}"
        logger.error(error_msg)
        raise

def test_extract_and_compress(file_path: str):
    """Test the extract and compress endpoints together"""
    # Validate file exists
    if not Path(file_path).is_file():
        logger.error(f"Test file not found: {file_path}")
        return False

    # 1. Extract metadata
    logger.info("\n" + "="*50)
    logger.info("EXTRACTING METADATA")
    logger.info("="*50)
    start_time = time.time()
    
    try:
        # Extract metadata
        extract_params = {
            "filePath": file_path,
            "rows_per_chunk": 10,
            "max_cols_per_sheet": 50,
            "include_dependencies": True,
            "include_empty_chunks": False
        }
        
        extract_response = make_request("POST", EXTRACT_ENDPOINT, extract_params)
        chunks = extract_response.get("chunks", [])
        extract_duration = time.time() - start_time
        
        logger.info(f"Extraction completed in {extract_duration:.2f} seconds")
        logger.info(f"Extracted {len(chunks)} chunks")
        
        if not chunks:
            logger.error("No chunks were extracted")
            return False

        # 2. Compress the extracted chunks
        logger.info("\n" + "="*50)
        logger.info("COMPRESSING CHUNKS")
        logger.info("="*50)
        compress_start = time.time()
        
        compress_params = {
            "chunks": chunks,
            "max_cells_per_chunk": 1000,
            "max_cell_length": 200
        }
        
        compress_response = make_request("POST", COMPRESS_ENDPOINT, compress_params)
        compress_duration = time.time() - compress_start
        
        compressed_texts = compress_response.get("compressed_texts", [])
        compressed_markdown_texts = compress_response.get("compressed_markdown_texts", [])
        
        logger.info(f"Compression completed in {compress_duration:.2f} seconds")
        logger.info(f"Original chunks: {len(chunks)}")
        logger.info(f"Compressed texts: {len(compressed_texts)}")
        logger.info(f"Compressed markdown texts: {len(compressed_markdown_texts)}")
        
        # Simple validation
        if len(compressed_texts) != len(compressed_markdown_texts):
            logger.warning("Mismatch between number of compressed texts and markdown texts")
            
        if len(compressed_texts) == 0:
            logger.error("No compressed texts were generated")
            return False
            
        # Log sample compressed output
        logger.info("\nSample compressed text:")
        logger.info(compressed_texts[0][:500] + "...")  # First 500 chars of first chunk
        
        return True
        
    except Exception as e:
        logger.error(f"Test failed with error: {str(e)}", exc_info=True)
        return False

if __name__ == "__main__":
    try:
        logger.info("Starting extract and compress test...")
        success = test_extract_and_compress(TEST_FILE)
        
        if success:
            logger.info("\n✅ TEST PASSED: Extraction and compression completed successfully")
        else:
            logger.error("\n❌ TEST FAILED: Check logs for details")
            
    except Exception as e:
        logger.error(f"\n❌ TEST FAILED WITH EXCEPTION: {str(e)}", exc_info=True)