import requests
import json
import logging
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('edit_workflow_test.log')
    ]
)
logger = logging.getLogger(__name__)

# Configuration
BASE_URL = "http://127.0.0.1:3001/api"
TEST_FILE = r"C:\Users\shrey\OneDrive\Desktop\docs\test\single_tab_no_error.xlsx"  # From extract_compress_test.py

# Endpoints
EXTRACT_ENDPOINT = "/excel/extract-metadata-chunks"
COMPRESS_ENDPOINT = "/excel/compress-chunks"
EDIT_ENDPOINT = f"{BASE_URL}/excel/edit-excel"
ACCEPT_ENDPOINT = f"{BASE_URL}/excel/edits/accept"

def make_request(method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
    """Helper function to make HTTP requests with error handling and logging"""
    url = f"{BASE_URL}{endpoint}" if endpoint.startswith('/') else endpoint
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

def extract_metadata(file_path: str) -> List[Dict]:
    """Extract metadata from Excel file"""
    logger.info("\n" + "="*50)
    logger.info("EXTRACTING METADATA")
    logger.info("="*50)
    
    extract_params = {
        "filePath": file_path,
        "rows_per_chunk": 10,
        "max_cols_per_sheet": 50,
        "include_dependencies": True,
        "include_empty_chunks": False
    }
    
    response = make_request("POST", EXTRACT_ENDPOINT, extract_params)
    chunks = response.get("chunks", [])
    logger.info(f"Extracted {len(chunks)} chunks")
    return chunks

def compress_chunks(chunks: List[Dict]) -> Dict:
    """Compress extracted chunks"""
    logger.info("\n" + "="*50)
    logger.info("COMPRESSING CHUNKS")
    logger.info("="*50)
    
    compress_params = {
        "chunks": chunks,
        "max_cells_per_chunk": 1000,
        "max_cell_length": 200
    }
    
    response = make_request("POST", COMPRESS_ENDPOINT, compress_params)
    return response

def make_edit(file_path: str) -> Dict:
    """Make an edit to trigger embedding update"""
    logger.info("\n" + "="*50)
    logger.info("MAKING EDIT")
    logger.info("="*50)
    
    edit_data = {
        "file_path": file_path,
        "metadata": {
            "Sheet1": [{
                "cell": "A1",
                "formula": "Updated Title " + str(int(time.time())),  # Make it unique
                "font_style": "Arial",
                "font_size": 14,
                "bold": True,
                "text_color": "#2D5A27",
                "horizontal_alignment": "center",
                "vertical_alignment": "center"
            }]
        }
    }
    
    response = make_request("POST", EDIT_ENDPOINT, edit_data)
    logger.info(f"Edit response: {json.dumps(response, indent=2)}")
    return response

def accept_edits(edit_response: Dict) -> Dict:
    """Accept the pending edits to trigger embedding update"""
    logger.info("\n" + "="*50)
    logger.info("ACCEPTING EDITS")
    logger.info("="*50)
    
    edit_ids = [edit['edit_id'] for edit in edit_response.get('request_pending_edits', [])]
    if not edit_ids:
        logger.warning("No edit IDs to accept")
        return {}
        
    accept_data = {"edit_ids": edit_ids}
    response = make_request("POST", ACCEPT_ENDPOINT, accept_data)
    logger.info(f"Accept response: {json.dumps(response, indent=2)}")
    return response

def check_and_download_versions(file_path: str) -> bool:
    """Check available versions and download them"""
    logger.info("\n" + "="*50)
    logger.info("CHECKING VERSIONS")
    logger.info("="*50)
    
    try:
        # URL encode the file path
        from urllib.parse import quote
        encoded_file_path = quote(file_path, safe='')
        
        # Get list of versions
        versions_url = f"{BASE_URL}/excel/versioning/{encoded_file_path}/versions"
        versions_response = make_request("GET", versions_url)
        
        if not versions_response or not isinstance(versions_response, list):
            logger.error("Failed to get versions or no versions found")
            return False
            
        logger.info(f"Found {len(versions_response)} versions:")
        for i, version in enumerate(versions_response, 1):
            logger.info(f"Version {i}: ID={version['version_id']}, Number={version['version_number']}, Created={version['created_at']}")
            
        # Download each version
        for version in versions_response:
            # The download URL is already absolute in the response, so we can use it directly
            download_url = version['download_url']
            download_path = f"version_{version['version_number']}.xlsx"
            
            logger.info(f"Downloading version {version['version_number']} from {download_url}...")
            response = requests.get(download_url)
            response.raise_for_status()
            
            with open(download_path, 'wb') as f:
                f.write(response.content)
            logger.info(f"Saved version {version['version_number']} to {download_path}")
            
        return True
        
    except Exception as e:
        logger.error(f"Error checking/downloading versions: {str(e)}", exc_info=True)
        return False

def test_workflow():
    """Test the complete workflow"""
    try:
        # 1. Extract metadata
        chunks = extract_metadata(TEST_FILE)
        if not chunks:
            logger.error("No chunks extracted, aborting test")
            return False

        # 2. Compress chunks
        compress_response = compress_chunks(chunks)
        if not compress_response.get('compressed_texts'):
            logger.error("No compressed texts generated, aborting test")
            return False

        # 3. Make an edit to trigger embedding update
        edit_response = make_edit(TEST_FILE)
        if 'request_pending_edits' not in edit_response:
            logger.error("No pending edits in response, aborting test")
            return False

        # 4. Accept the edits to trigger embedding update
        accept_response = accept_edits(edit_response)
        if not accept_response.get('success', False):
            logger.error("Failed to accept edits")
            return False

        # 5. Check and download versions
        if not check_and_download_versions(TEST_FILE):
            logger.error("Failed to check/download versions")
            return False

        logger.info("\n" + "="*50)
        logger.info("WORKFLOW COMPLETED SUCCESSFULLY")
        logger.info("="*50)
        logger.info("Check the server logs for embedding worker output")
        logger.info("Look for messages like 'Processing embedding task' and 'Successfully stored'")
        logger.info("Check the downloaded version files in the current directory")
        
        return True

    except Exception as e:
        logger.error(f"Workflow failed: {str(e)}", exc_info=True)
        return False

if __name__ == "__main__":
    try:
        logger.info("Starting edit workflow test...")
        success = test_workflow()
        
        if success:
            logger.info("\n✅ TEST PASSED: Edit workflow completed successfully")
            logger.info("Check the server logs for embedding worker output")
        else:
            logger.error("\n❌ TEST FAILED: Check logs for details")
            
    except Exception as e:
        logger.error(f"\n❌ TEST FAILED WITH EXCEPTION: {str(e)}", exc_info=True)