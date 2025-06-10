import requests
import json
import argparse
from typing import Dict, Any

# API configuration
BASE_URL = "http://localhost:3001/api"
EXCEL_BASE = f"{BASE_URL}/excel"
VECTORS_BASE = f"{BASE_URL}/vectors"

def extract_metadata_chunks(file_path: str, rows_per_chunk: int = 10) -> Dict[str, Any]:
    """Extract metadata chunks from an Excel file."""
    url = f"{EXCEL_BASE}/extract-metadata-chunks"
    payload = {
        "filePath": file_path,
        "rows_per_chunk": rows_per_chunk,
        "max_cols_per_sheet": 50,
        "include_dependencies": True,
        "include_empty_chunks": False
    }
    
    print(f"Extracting metadata chunks from: {file_path}")
    response = requests.post(url, json=payload)
    response.raise_for_status()
    return response.json()

def compress_chunks(chunks: list) -> Dict[str, Any]:
    """Compress metadata chunks to text."""
    url = f"{EXCEL_BASE}/compress-chunks"
    payload = {
        "chunks": chunks,
        "max_cells_per_chunk": 1000,
        "max_cell_length": 200
    }
    
    print(f"Compressing {len(chunks)} chunks...")
    response = requests.post(url, json=payload)
    response.raise_for_status()
    return response.json()

def store_embeddings(workbook_path: str, chunks: list, model_name: str = "msmarco-MiniLM-L-6-v3") -> Dict[str, Any]:
    """Store embeddings for the given chunks."""
    url = f"{VECTORS_BASE}/storage/embed-and-store-chunks"
    payload = {
        "workbook_path": workbook_path,
        "chunks": chunks,
        "embedding_model": model_name,
        "replace_existing": True
    }
    
    print(f"Storing embeddings for workbook: {workbook_path}")
    response = requests.post(url, json=payload)
    response.raise_for_status()
    return response.json()

def search_embeddings(workbook_path: str, query: str, top_k: int = 5) -> Dict[str, Any]:
    """Search stored embeddings."""
    url = f"{VECTORS_BASE}/search/query"
    payload = {
        "query": query,
        "workbook_path": workbook_path,
        "top_k": top_k,
        "return_format": "both"  # Get both text and markdown
    }
    
    print(f"Searching for: '{query}'")
    response = requests.post(url, json=payload)
    response.raise_for_status()
    return response.json()

def ask_question(search_response: Dict[str, Any], question: str, model: str = "claude-sonnet-4-20250514") -> None:
    """Ask a question based on search results and stream the response."""
    url = f"{EXCEL_BASE}/qa/from-search"
    payload = {
        "search_response": search_response,
        "question": question,
        "model": model,
        "include_chunk_sources": True
    }
    
    print(f"\n=== Asking Question ===")
    print(f"Question: {question}")
    print("\nAnswer:")
    
    try:
        with requests.post(url, json=payload, stream=True) as response:
            response.raise_for_status()
            
            buffer = ""
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith('data: '):
                        data = line[6:]  # Remove 'data: ' prefix
                        if data == '[DONE]':
                            break
                            
                        try:
                            chunk_data = json.loads(data)
                            if 'chunk' in chunk_data:
                                chunk = chunk_data['chunk']
                                print(chunk, end='', flush=True)
                            elif 'error' in chunk_data:
                                print(f"\nError: {chunk_data['error']}")
                                break
                        except json.JSONDecodeError:
                            print(f"\nFailed to parse chunk: {data}")
                            
    except requests.exceptions.RequestException as e:
        print(f"\nError making QA request: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"Response: {e.response.text}")


def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Test Excel metadata extraction, storage, and search')
    parser.add_argument('--file_path', type=str, default=r"C:\Users\shrey\OneDrive\Desktop\docs\test\single_tab_no_error.xlsx", help='Path to the Excel file')
    parser.add_argument('--query', type=str, default="explain the income statement trends", help='Search query')
    parser.add_argument('--rows', type=int, default=10, help='Number of rows per chunk (default: 10)')
    parser.add_argument('--top_k', type=int, default=3, help='Number of search results to return (default: 3)')
    args = parser.parse_args()

    try:
        # Step 1: Extract metadata chunks
        print("\n=== Extracting Metadata Chunks ===")
        extract_result = extract_metadata_chunks(args.file_path, args.rows)
        chunks = extract_result.get('chunks', [])
        print(f"Extracted {len(chunks)} metadata chunks")
        
        if not chunks:
            print("No chunks were extracted")
            return

        # Step 2: Compress chunks to text and markdown
        print("\n=== Compressing Chunks ===")
        compress_result = compress_chunks(chunks)
        compressed_texts = compress_result.get('compressed_texts', [])
        compressed_markdown = compress_result.get('compressed_markdown_texts', [])
        
        # Combine original chunks with compressed versions
        enhanced_chunks = []
        for i, (chunk, text, md) in enumerate(zip(chunks, compressed_texts, compressed_markdown)):
            enhanced = chunk.copy()
            enhanced['text'] = text
            enhanced['markdown'] = md
            enhanced_chunks.append(enhanced)
        
        # Step 3: Store embeddings
        print("\n=== Storing Embeddings ===")
        store_result = store_embeddings(args.file_path, enhanced_chunks)
        print(f"Stored {store_result.get('chunks_stored', 0)} chunks")
        
        # Step 4: Search embeddings
        print("\n=== Searching Embeddings ===")
        search_result = search_embeddings(args.file_path, args.query, args.top_k)
        
        # Print search results
        print(f"\nSearch Results for: '{args.query}'")
        print("=" * 80)
        
        for i, result in enumerate(search_result.get('results', []), 1):
            print(f"\n--- Result {i} (Score: {result.get('score', 0):.4f}) ---")
            
            # Print text preview
            text = result.get('text', '').replace('\n', ' ').strip()
            print("\nText Preview:")
            print(f"{text[:200]}..." if len(text) > 200 else text)
            
            # Print markdown preview
            markdown = result.get('markdown', '').replace('\n', ' ').strip()
            print("\nMarkdown Preview:")
            print(f"{markdown[:200]}..." if len(markdown) > 200 else markdown)
            
            print("-" * 80)


        # Step 5: Ask a question based on search results
        if args.query:
            ask_question(search_result, args.query)

    except requests.exceptions.RequestException as e:
        print(f"\nError making request: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"Response: {e.response.text}")
    except Exception as e:
        print(f"\nAn error occurred: {e}")

if __name__ == "__main__":
    main()