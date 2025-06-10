import requests
import json
import time
from typing import Dict, Any, List, Optional

# Base URL for the API
BASE_URL = "http://127.0.0.1:3001/api"

# Test file path (using raw string to handle Windows paths)
TEST_FILE = r"C:\Users\shrey\OneDrive\Desktop\docs\test\full_create_model_flow_test.xlsx"

# Test query
TEST_QUERY = "add a line for the operating profit after tax under the operating profit and tax line, with formulaes to calculate the operating profit minus tax"

def make_request(method: str, endpoint: str, data: Optional[Dict] = None, params: Optional[Dict] = None) -> Dict[str, Any]:
    """Helper function to make HTTP requests with error handling"""
    url = f"{BASE_URL}{endpoint}"
    
    if method.upper() == "GET":
        response = requests.get(url, params=params)
    elif method.upper() == "POST":
        response = requests.post(url, json=data)
    else:
        raise ValueError(f"Unsupported HTTP method: {method}")
    
    response.raise_for_status()
    return response.json()


def test_entire_flow():
    print("Starting end-to-end test...\n")
    
    # 1. Extract metadata chunks
    print("Step 1: Extracting metadata chunks...")
    extract_response = make_request(
        "POST",
        "/excel/extract-metadata-chunks",
        {
            "filePath": TEST_FILE,
            "rows_per_chunk": 10,
            "max_cols_per_sheet": 50,
            "include_dependencies": True,
            "include_empty_chunks": False
        }
    )
    print("Metadata extraction complete.")
    chunks = extract_response.get("chunks", [])
    print(f"Extracted {len(chunks)} chunks.\n")
    
    # 2. Compress chunks
    print("Step 2: Compressing chunks...")
    compress_response = make_request(
        "POST",
        "/excel/compress-chunks",
        {
            "chunks": chunks,
            "max_cells_per_chunk": 1000,
            "max_cell_length": 200
        }
    )
    print("Chunks compressed.\n")

    # After the compress-chunks call
    compressed_texts = compress_response.get("compressed_texts", [])
    compressed_markdown_texts = compress_response.get("compressed_markdown_texts", [])

    # Update the chunks with compressed content
    for i, (text, markdown) in enumerate(zip(compressed_texts, compressed_markdown_texts)):
        if i < len(chunks):
            chunks[i]["text"] = text
            chunks[i]["markdown"] = markdown
        else:
            chunks.append({
                "text": text,
                "markdown": markdown,
                "metadata": {}
            })

    # Add this right before the store_embeddings call
    print("\nSending request to /vectors/storage/embed-and-store-chunks with data:")
    
    # 3. Store and embed chunks
    print("Step 3: Storing and embedding chunks...")
    store_response = make_request(
        "POST",
        "/vectors/storage/embed-and-store-chunks",
        {
            "workbook_path": TEST_FILE,
            "chunks": [{
                "text": chunk.get("text", ""),
                "markdown": chunk.get("markdown", ""),
                "metadata": chunk.get("metadata", {})
            } for chunk in chunks],
            "embedding_model": "msmarco-MiniLM-L-6-v3",
            "replace_existing": True
        }
    )
    print("Chunks stored and embedded.\n")
    
    # 4. Search embeddings (to find relevant chunks for our query)
    print("Step 4: Searching for relevant chunks...")
    search_response = make_request(
        "POST",
        "/vectors/search/query",
        {
            "query": "operating profit tax",
            "workbook_path": TEST_FILE,
            "top_k": 5,
            "return_format": "both"
        }
    )
    print(f"Found {len(search_response.get('results', []))} relevant chunks.\n")
    
    # 5. Generate edit metadata
    print("Step 5: Generating edit metadata...")
    generate_response = make_request(
        "POST",
        "/excel/generate-edit-metadata",
        {
            "user_request": TEST_QUERY,
            "chunks": [{
                "text": chunk["text"],
                "markdown": chunk["markdown"],
                "metadata": chunk.get("metadata", {})
            } for chunk in search_response.get("results", [])],
            "chunk_limit": 5,
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 2000,
            "temperature": 0.3,
            "stream": False
        }
    )
    print("Edit metadata generated.\n")
    
    # 6. Parse the generated metadata
    print("Step 6: Parsing generated metadata...")
    parse_response = make_request(
        "POST",
        "/excel/parse-metadata",
        {
            "metadata": generate_response.get("result", ""),
            "strict": True
        }
    )
    print("Metadata parsed successfully.\n")
    
    # 7. Apply the edit
    print("Step 7: Applying edit to Excel file...")
    apply_response = make_request(
        "POST",
        "/excel/edit-excel",
        {
            "file_path": TEST_FILE,
            "metadata": parse_response.get("data", {}),
            "visible": False
        }
    )
    print(f"Edit applied successfully. Modified sheets: {', '.join(apply_response.get('modified_sheets', []))}\n")
    
    print("Test completed successfully!")

if __name__ == "__main__":
    try:
        test_entire_flow()
    except Exception as e:
        print(f"\nTest failed with error: {str(e)}")
        raise