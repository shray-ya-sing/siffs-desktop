import json
import os
from pathlib import Path

def split_json_file(input_file, output_dir):
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Read the input JSON file
    with open(input_file, 'r', encoding='utf-8') as f:
        chunks = json.load(f)
    
    # Process each chunk
    for i, chunk in enumerate(chunks):
        # Create output filename with leading zeros
        output_file = os.path.join(output_dir, f"chunk_{i:03d}.json")
        
        # Write the chunk to a separate JSON file
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(chunk, f, indent=2, ensure_ascii=False)
        
        print(f"Created: {output_file}")
    
    print(f"\nSuccessfully split {len(chunks)} chunks into separate JSON files.")

if __name__ == "__main__":
    # Define input and output paths
    input_file = r"C:\Users\shrey\projects\cori-apps\cori_app\src\evals\scripts\vectors\retrieval_accuracy\data\test_1\json\raw_chunks.json"
    output_dir = r"C:\Users\shrey\projects\cori-apps\cori_app\src\evals\scripts\vectors\retrieval_accuracy\data\test_1\json\chunks"
    
    # Split the JSON file
    split_json_file(input_file, output_dir)