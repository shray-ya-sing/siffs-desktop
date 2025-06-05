import requests
import json
import argparse
from typing import Dict, Any

# API configuration
BASE_URL = "http://localhost:3001/api/excel"

def extract_metadata_chunks(file_path: str, rows_per_chunk: int = 10) -> Dict[str, Any]:
    """Extract metadata chunks from an Excel file."""
    url = f"{BASE_URL}/extract-metadata-chunks"
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
    url = f"{BASE_URL}/compress-chunks"
    payload = {
        "chunks": chunks,
        "max_cells_per_chunk": 1000,
        "max_cell_length": 200
    }
    
    print(f"Compressing {len(chunks)} chunks...")
    response = requests.post(url, json=payload)
    response.raise_for_status()
    return response.json()

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Test Excel metadata extraction and compression')
    parser.add_argument('file_path', type=str, help='Path to the Excel file')
    parser.add_argument('--rows', type=int, default=10, help='Number of rows per chunk (default: 10)')
    args = parser.parse_args()

    try:
        # Step 1: Extract metadata chunks
        extract_result = extract_metadata_chunks(args.file_path, args.rows)
        chunks = extract_result.get('chunks', [])
        print(f"Extracted {len(chunks)} metadata chunks")
        
        if not chunks:
            print("No chunks were extracted")
            return

        # Step 2: Compress chunks to text
        compress_result = compress_chunks(chunks)
        compressed_texts = compress_result.get('compressed_texts', [])
        print(f"\nCompressed to {len(compressed_texts)} text chunks")
        
        # Print statistics
        stats = compress_result.get('statistics', {})
        print(f"\nStatistics:")
        print(f"Total characters: {stats.get('total_characters', 0):,}")
        print(f"Avg. chars per chunk: {stats.get('average_characters_per_chunk', 0):,.0f}")
        
        # Print first 200 chars of each chunk
        print("\nFirst 200 characters of each chunk:")
        for i, text in enumerate(compressed_texts, 1):
            preview = text[:200].replace('\n', ' ').strip()
            print(f"\n--- Chunk {i} ---")
            print(f"{preview}...")
            if i >= 5:  # Limit to first 5 chunks for brevity
                remaining = len(compressed_texts) - 5
                if remaining > 0:
                    print(f"\n... and {remaining} more chunks")
                break

        compressed_markdown_texts = compress_result.get('compressed_markdown_texts', [])
        print(f"\nCompressed to {len(compressed_markdown_texts)} markdown chunks")
        
        # Print first 200 chars of each chunk
        print("\nFirst 200 characters of each chunk:")
        for i, text in enumerate(compressed_markdown_texts, 1):
            preview = text[:200].replace('\n', ' ').strip()
            print(f"\n--- Chunk {i} ---")
            print(f"{preview}...")
            if i >= 5:  # Limit to first 5 chunks for brevity
                remaining = len(compressed_markdown_texts) - 5
                if remaining > 0:
                    print(f"\n... and {remaining} more chunks")
                break

    except requests.exceptions.RequestException as e:
        print(f"Error making request: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"Response: {e.response.text}")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()