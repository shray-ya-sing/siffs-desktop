import os
import json
import requests
from pathlib import Path
from typing import List, Dict, Any
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
BASE_URL = "http://localhost:3001/api"  # Dev server URL
FILE_PATH = r"C:\Users\shrey\OneDrive\Desktop\docs\test\test_model_Alibaba_IPO(shorter)_llm.xlsx"
OUTPUT_DIR = Path(__file__).parent / "data"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def extract_chunks(file_path: str, rows_per_chunk: int = 10) -> List[Dict[str, Any]]:
    """Extract metadata chunks from Excel file."""
    logger.info(f"Extracting chunks from {file_path}")
    
    response = requests.post(
        f"{BASE_URL}/excel/extract-metadata-chunks",
        json={
            "filePath": file_path,
            "rows_per_chunk": rows_per_chunk,
            "include_dependencies": True,
            "include_empty_chunks": False
        }
    )
    response.raise_for_status()
    
    data = response.json()
    logger.info(f"Extracted {data['chunkCount']} chunks")
    return data["chunks"]

def compress_chunks(chunks: List[Dict[str, Any]]) -> Dict[str, List[str]]:
    """Compress chunks to natural text and markdown."""
    logger.info(f"Compressing {len(chunks)} chunks")
    
    response = requests.post(
        f"{BASE_URL}/excel/compress-chunks",
        json={
            "chunks": chunks,
            "max_cells_per_chunk": 100,
            "max_cell_length": 1000
        }
    )
    response.raise_for_status()
    
    return response.json()

def save_results(chunks: List[Dict[str, Any]], compressed_data: Dict[str, List[str]]) -> None:
    """Save chunks and compressed versions to files."""
    # Save raw chunks
    chunks_file = OUTPUT_DIR / "raw_chunks.json"
    with open(chunks_file, 'w', encoding='utf-8') as f:
        json.dump(chunks, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved raw chunks to {chunks_file}")

    # Save compressed texts
    for i, (text, markdown) in enumerate(zip(
        compressed_data["compressed_texts"],
        compressed_data["compressed_markdown_texts"]
    )):
        # Save natural text
        text_file = OUTPUT_DIR / f"chunk_{i:03d}_natural.txt"
        with open(text_file, 'w', encoding='utf-8') as f:
            f.write(text)
        
        # Save markdown
        md_file = OUTPUT_DIR / f"chunk_{i:03d}_markdown.md"
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(markdown)
    
    # Save metadata
    metadata = {
        "chunk_count": len(chunks),
        "statistics": compressed_data.get("statistics", {})
    }
    with open(OUTPUT_DIR / "metadata.json", 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2)
    
    logger.info(f"Saved {len(chunks)} compressed chunks to {OUTPUT_DIR}")

def main():
    try:
        # Step 1: Extract chunks
        chunks = extract_chunks(FILE_PATH)
        
        # Step 2: Compress chunks
        compressed_data = compress_chunks(chunks)
        
        # Step 3: Save results
        save_results(chunks, compressed_data)
        
        logger.info("Extraction and compression completed successfully")
        
    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    main()