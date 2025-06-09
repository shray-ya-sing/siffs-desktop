# test_full_workflow.py
import requests
import json
import os
import time
from pathlib import Path
import pprint

# Configuration
BASE_URL = "http://127.0.0.1:3001"
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

# Test file path
OUTPUT_FILE = r"C:\Users\shrey\OneDrive\Desktop\docs\test\full_create_model_flow_test.xlsx"

# Sample request for financial analysis
SAMPLE_QUERY = """
Create a financial analysis spreadsheet with the following:
1. Quarterly revenue forecast for 2025-2026
2. Starting revenue of $100,000 in Q1 2025 with 10% quarterly growth
3. Expense categories: COGS (40% of revenue), Salaries ($20,000/quarter), Marketing (15% of revenue)
4. Calculate Gross Profit, Operating Income, and Net Income (20% tax rate)
5. Include appropriate number formatting and styling
"""

def generate_metadata(query: str) -> str:
    """Generate metadata using the LLM."""
    print("\n=== Step 1: Generating Metadata ===")
    url = f"{BASE_URL}/api/excel/generate-metadata"
    
    try:
        response = requests.post(
            url,
            json={
                "user_request": query,
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 2000,
                "temperature": 0.3,
                "stream": False
            },
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            metadata = result.get("result", "")
            print("✅ Metadata generated successfully")
            
            # Save the generated metadata
            metadata_file = OUTPUT_DIR / "generated_metadata.txt"
            with open(metadata_file, "w", encoding="utf-8") as f:
                f.write(metadata)
            print(f"📄 Metadata saved to: {metadata_file}")
            
            return metadata
        else:
            print(f"❌ Error generating metadata: {response.status_code}")
            print(response.text)
            return None
            
    except Exception as e:
        print(f"❌ Request failed: {str(e)}")
        return None

def parse_metadata(metadata: str) -> dict:
    """Parse the generated metadata into structured format."""
    print("\n=== Step 2: Parsing Metadata ===")
    url = f"{BASE_URL}/api/excel/parse-metadata"
    
    try:
        response = requests.post(
            url,
            json={
                "metadata": metadata,
                "strict": True
            },
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Metadata parsed successfully")
            
            # Save the parsed metadata
            parsed_file = OUTPUT_DIR / "parsed_metadata.json"
            with open(parsed_file, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2)
            print(f"📄 Parsed metadata saved to: {parsed_file}")
            
            return result.get("data")
        else:
            print(f"❌ Error parsing metadata: {response.status_code}")
            print(response.text)
            return None
            
    except Exception as e:
        print(f"❌ Request failed: {str(e)}")
        return None

def edit_excel(file_path: str, metadata: dict) -> bool:
    """Apply the metadata to an Excel file."""
    print("\n=== Step 3: Creating Excel File ===")
    url = f"{BASE_URL}/api/excel/create-excel"
    
    try:
        # Ensure the directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        response = requests.post(
            url,
            json={
                "file_path": file_path,
                "metadata": metadata,
                "visible": False
            },
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Excel file created successfully")
            print(f"📊 File saved to: {file_path}")
            print(f"Modified sheets: {', '.join(result.get('modified_sheets', []))}")
            return True
        else:
            print(f"❌ Error creating Excel file: {response.status_code}")
            print(response.text)
            return False
            
    except Exception as e:
        print(f"❌ Request failed: {str(e)}")
        return False

def main():
    print("=== Testing Full Model Creation Workflow ===")
    print(f"Output file will be saved to: {OUTPUT_FILE}")
    
    # Step 1: Generate metadata
    metadata = generate_metadata(SAMPLE_QUERY)
    if not metadata:
        print("❌ Workflow failed at metadata generation")
        return
    
    # Step 2: Parse metadata
    parsed_data = parse_metadata(metadata)
    if not parsed_data:
        print("❌ Workflow failed at metadata parsing")
        return
    
    # Step 3: Create Excel file
    if not edit_excel(OUTPUT_FILE, parsed_data):
        print("❌ Workflow failed at Excel file creation")
        return
    
    print("\n🎉 Workflow completed successfully! 🎉")

if __name__ == "__main__":
    start_time = time.time()
    main()
    print(f"\nTotal execution time: {time.time() - start_time:.2f} seconds")