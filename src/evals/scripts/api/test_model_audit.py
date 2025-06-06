import os
import sys
import json
import requests
from typing import Dict, Any, Optional
from pathlib import Path

# Configuration
BASE_URL = "http://127.0.0.1:3001/api/excel"
TEST_FILE = Path(r"C:\Users\shrey\OneDrive\Desktop\docs\test\test_model_Alibaba_IPO(shorter)_llm.xlsx")

def check_dependencies():
    try:
        import requests
    except ImportError:
        print("Error: Required package 'requests' not installed. Install with: pip install requests")
        sys.exit(1)

def log_step(step: str, message: str):
    print(f"\n{'='*50}")
    print(f"STEP: {step}")
    print(f"{'='*50}")
    print(message)

def log_response(response: requests.Response, success_msg: str, error_msg: str) -> bool:
    try:
        if 200 <= response.status_code < 300:
            log_step("SUCCESS", success_msg)
            return True
        else:
            error_details = {
                "status_code": response.status_code,
                "reason": response.reason,
                "text": response.text[:500] + "..." if len(response.text) > 500 else response.text
            }
            log_step("ERROR", f"{error_msg}\nDetails: {json.dumps(error_details, indent=2)}")
            return False
    except Exception as e:
        log_step("EXCEPTION", f"Error logging response: {str(e)}")
        return False

def test_extract_metadata(file_path: Path) -> Optional[Dict[str, Any]]:
    log_step("1. EXTRACTING METADATA", f"Extracting metadata from: {file_path}")
    
    if not file_path.exists():
        log_step("ERROR", f"File not found: {file_path}")
        return None
    
    try:
        response = requests.post(
            f"{BASE_URL}/extract-metadata",
            json={
                'filePath': str(file_path),
                'max_rows_per_sheet': 100,
                'max_cols_per_sheet': 50,
                'include_display_values': True
            },
            timeout=60  # 60 seconds timeout
        )
        
        if log_response(response, 
                       "Successfully extracted metadata", 
                       "Failed to extract metadata"):
            result = response.json()
            if 'metadata' not in result or 'display_values' not in result:
                log_step("ERROR", "Response missing required fields: 'metadata' or 'display_values'")
                return None
            return result
        return None
        
    except requests.exceptions.RequestException as e:
        log_step("NETWORK ERROR", f"Request failed: {str(e)}")
        return None
    except Exception as e:
        log_step("EXCEPTION", f"Error in extract_metadata: {str(e)}")
        return None

def test_compress_metadata(metadata: Dict[str, Any], display_values: Dict[str, Any]) -> Optional[str]:
    log_step("2. COMPRESSING METADATA", "Converting metadata to markdown format")
    
    try:
        response = requests.post(
            f"{BASE_URL}/compress-metadata",
            json={
                'metadata': metadata,
                'display_values': display_values
            },
            timeout=60
        )
        
        if log_response(response, 
                       "Successfully compressed metadata to markdown", 
                       "Failed to compress metadata"):
            result = response.json()
            if 'markdown' not in result:
                log_step("ERROR", "Response missing 'markdown' field")
                return None
            log_step("MARKDOWN PREVIEW", result['markdown'][:500] + "...")
            return result['markdown']
        return None
        
    except requests.exceptions.RequestException as e:
        log_step("NETWORK ERROR", f"Request failed: {str(e)}")
        return None
    except Exception as e:
        log_step("EXCEPTION", f"Error in compress_metadata: {str(e)}")
        return None

def test_chunk_markdown(markdown: str) -> Optional[Dict[str, Any]]:
    log_step("3. CHUNKING MARKDOWN", "Splitting markdown into chunks")
    
    try:
        response = requests.post(
            f"{BASE_URL}/chunk-metadata",
            json={
                'markdown': markdown,
                'max_tokens': 18000
            },
            timeout=60
        )
        
        if log_response(response, 
                       "Successfully chunked markdown", 
                       "Failed to chunk markdown"):
            result = response.json()
            if 'chunks' not in result or 'chunk_info' not in result:
                log_step("ERROR", "Response missing required fields: 'chunks' or 'chunk_info'")
                return None
                
            log_step("CHUNK INFO", f"Created {len(result['chunks'])} chunks")
            for i, chunk in enumerate(result['chunks'][:3]):
                preview = chunk[:200] + "..." if len(chunk) > 200 else chunk
                log_step(f"CHUNK {i+1} PREVIEW", preview)
            return result
        return None
        
    except requests.exceptions.RequestException as e:
        log_step("NETWORK ERROR", f"Request failed: {str(e)}")
        return None
    except Exception as e:
        log_step("EXCEPTION", f"Error in chunk_markdown: {str(e)}")
        return None

def test_analyze_chunks(chunks: list) -> bool:
    log_step("4. ANALYZING CHUNKS", f"Analyzing {len(chunks)} chunks")
    
    try:
        response = requests.post(
            f"{BASE_URL}/analyze-chunks",
            json={
                'chunks': chunks,
                'model': 'claude-sonnet-4-20250514',
                'temperature': 0.3,
                'max_tokens': 1000
            },
            stream=True,
            timeout=300  # 5 minutes timeout for analysis
        )
        
        if not log_response(response, 
                          "Started chunk analysis stream", 
                          "Failed to start analysis"):
            return False
            
        log_step("ANALYSIS STREAM", "Starting analysis stream (first 5 chunks)...")
        chunk_count = 0
        error_occurred = False
        
        for line in response.iter_lines():
            if line:
                try:
                    chunk = line.decode('utf-8').strip()
                    if not chunk:
                        continue
                        
                    if chunk.startswith('data: '):
                        chunk = chunk[6:].strip()
                        if chunk == '[DONE]':
                            log_step("ANALYSIS COMPLETE", "Received DONE signal")
                            break
                            
                        try:
                            data = json.loads(chunk)
                            if 'error' in data:
                                log_step("ANALYSIS ERROR", f"Error in analysis: {data['error']}")
                                error_occurred = True
                                break
                            elif 'chunk' in data:
                                chunk_count += 1
                                preview = data['chunk'][:200] + "..." if len(data['chunk']) > 200 else data['chunk']
                                print(f"\nChunk {chunk_count}:\n{preview}")
                                if chunk_count >= 5:
                                    log_step("STREAM PREVIEW", "Showing first 5 chunks. Analysis continuing in background...")
                                    break
                            elif 'info' in data:
                                print(f"\n[INFO] {data['info'].strip()}")
                        except json.JSONDecodeError:
                            print(f"\n[RAW] {chunk[:200]}...")
                except UnicodeDecodeError:
                    print(f"\n[INVALID UTF-8 DATA] {line[:100]}...")
        
        if error_occurred:
            return False
            
        log_step("ANALYSIS SUMMARY", f"Processed {chunk_count} chunks")
        return True
        
    except requests.exceptions.RequestException as e:
        log_step("NETWORK ERROR", f"Request failed: {str(e)}")
        return False
    except Exception as e:
        log_step("EXCEPTION", f"Error in analyze_chunks: {str(e)}")
        return False

def main():
    print("\n" + "="*70)
    print("MODEL AUDIT PIPELINE TEST")
    print("="*70)
    
    # Check dependencies
    check_dependencies()
    
    # 1. Test metadata extraction
    extract_result = test_extract_metadata(TEST_FILE)
    if not extract_result:
        print("\n❌ Failed at metadata extraction step. Exiting.")
        return
        
    # 2. Test metadata compression
    markdown = test_compress_metadata(
        extract_result['metadata'], 
        extract_result.get('display_values', {})
    )
    if not markdown:
        print("\n❌ Failed at metadata compression step. Exiting.")
        return
        
    # 3. Test markdown chunking
    chunk_result = test_chunk_markdown(markdown)
    if not chunk_result:
        print("\n❌ Failed at markdown chunking step. Exiting.")
        return
        
    # 4. Test chunk analysis
    if not test_analyze_chunks(chunk_result['chunks']):
        print("\n❌ Failed at chunk analysis step. Exiting.")
        return
        
    print("\n" + "="*70)
    print("✅ PIPELINE TEST COMPLETED SUCCESSFULLY")
    print("="*70)

if __name__ == "__main__":
    main()