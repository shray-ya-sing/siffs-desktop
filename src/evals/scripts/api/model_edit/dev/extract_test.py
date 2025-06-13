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
        logging.FileHandler('extract_test.log')
    ]
)
logger = logging.getLogger(__name__)

# Configuration
BASE_URL = "http://127.0.0.1:3001/api"
TEST_FILE = r"C:\Users\shrey\OneDrive\Desktop\docs\test\single_tab_no_error.xlsx"
EXTRACT_ENDPOINT = "/excel/extract-metadata-chunks"

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

def test_extract_endpoint(file_path: str):
    """Test the extract endpoint by calling it twice with the same file"""
    # Validate file exists
    if not Path(file_path).is_file():
        logger.error(f"Test file not found: {file_path}")
        return False

    extract_params = {
        "filePath": file_path,
        "rows_per_chunk": 10,
        "max_cols_per_sheet": 50,
        "include_dependencies": True,
        "include_empty_chunks": False
    }

    results = []
    
    # First extraction
    logger.info("\n" + "="*50)
    logger.info("FIRST EXTRACTION")
    logger.info("="*50)
    start_time = time.time()
    
    try:
        response1 = make_request("POST", EXTRACT_ENDPOINT, extract_params)
        duration1 = time.time() - start_time
        chunks1 = response1.get("chunks", [])
        results.append({
            "attempt": 1,
            "status": "success",
            "duration": f"{duration1:.2f}s",
            "chunks_extracted": len(chunks1),
            "chunk_sample": chunks1[0] if chunks1 else None
        })
        logger.info(f"First extraction completed in {duration1:.2f} seconds")
        logger.info(f"Extracted {len(chunks1)} chunks")
    except Exception as e:
        results.append({
            "attempt": 1,
            "status": "failed",
            "error": str(e)
        })
        logger.error("First extraction failed")
        return False

    # Short delay between requests
    time.sleep(2)
    
    # Second extraction with the same file
    logger.info("\n" + "="*50)
    logger.info("SECOND EXTRACTION (SAME FILE)")
    logger.info("="*50)
    start_time = time.time()
    
    try:
        response2 = make_request("POST", EXTRACT_ENDPOINT, extract_params)
        duration2 = time.time() - start_time
        chunks2 = response2.get("chunks", [])
        results.append({
            "attempt": 2,
            "status": "success",
            "duration": f"{duration2:.2f}s",
            "chunks_extracted": len(chunks2),
            "chunk_sample": chunks2[0] if chunks2 else None
        })
        logger.info(f"Second extraction completed in {duration2:.2f} seconds")
        logger.info(f"Extracted {len(chunks2)} chunks")
    except Exception as e:
        results.append({
            "attempt": 2,
            "status": "failed",
            "error": str(e)
        })
        logger.error("Second extraction failed")
        return False

    # Compare results
    logger.info("\n" + "="*50)
    logger.info("TEST RESULTS")
    logger.info("="*50)
    
    # Check if both extractions were successful
    if results[0]["status"] == "success" and results[1]["status"] == "success":
        # Compare number of chunks
        chunk_count_match = results[0]["chunks_extracted"] == results[1]["chunks_extracted"]
        logger.info(f"Chunk count matches: {chunk_count_match} "
                   f"({results[0]['chunks_extracted']} vs {results[1]['chunks_extracted']})")
        
        # Compare first chunk structure (if any chunks exist)
        if results[0]["chunks_extracted"] > 0 and results[1]["chunks_extracted"] > 0:
            chunk_structure_match = (
                sorted(results[0]["chunk_sample"].keys()) == 
                sorted(results[1]["chunk_sample"].keys())
            )
            logger.info(f"Chunk structure matches: {chunk_structure_match}")
        else:
            logger.warning("No chunks to compare structure")
            
        # Performance comparison
        time_diff = float(results[1]["duration"].rstrip('s')) - float(results[0]["duration"].rstrip('s'))
        logger.info(f"Time difference: {time_diff:.2f}s (2nd - 1st)")
        
        # Check if second extraction was faster (caching working)
        if time_diff < 0:
            logger.info("Second extraction was faster (possible cache hit)")
        else:
            logger.info("First extraction was faster")
            
        return chunk_count_match
    else:
        logger.error("One or both extractions failed")
        return False

if __name__ == "__main__":
    try:
        logger.info("Starting extract endpoint test...")
        success = test_extract_endpoint(TEST_FILE)
        
        if success:
            logger.info("\n✅ TEST PASSED: Both extractions completed successfully")
        else:
            logger.error("\n❌ TEST FAILED: Check logs for details")
            
    except Exception as e:
        logger.error(f"\n❌ TEST FAILED WITH EXCEPTION: {str(e)}", exc_info=True)