# test_edit_excel.py
import requests
import json
import os
from pathlib import Path

# Test configuration
BASE_URL = "http://127.0.0.1:3001"  # Update with your server URL
ENDPOINT = f"{BASE_URL}/api/excel/edit-excel"

# Sample metadata for testing
SAMPLE_METADATA = {
    "file_path": r"C:\Users\shrey\OneDrive\Desktop\docs\test\test_excel_writer.xlsx",
    "metadata": {
        "Sheet1": [
            {
                "cell": "A1",
                "formula": "Test Spreadsheet",
                "font_style": "Arial",
                "font_size": 14,
                "bold": True,
                "text_color": "#000000",
                "horizontal_alignment": "center",
                "vertical_alignment": "center",
                "number_format": "@",
                "fill_color": "#D9EAD3",
                "wrap_text": True
            },
            {
                "cell": "A2",
                "formula": "Product",
                "font_style": "Arial",
                "font_size": 12,
                "bold": True,
                "fill_color": "#E6E6E6"
            },
            {
                "cell": "B2",
                "formula": "Price",
                "font_style": "Arial",
                "font_size": 12,
                "bold": True,
                "horizontal_alignment": "right",
                "fill_color": "#E6E6E6",
                "number_format": "$#,##0.00"
            },
            {
                "cell": "A3",
                "formula": "Laptop",
                "font_style": "Arial"
            },
            {
                "cell": "B3",
                "formula": "1200",
                "number_format": "$#,##0.00"
            },
            {
                "cell": "A4",
                "formula": "Total",
                "font_style": "Arial",
                "bold": True
            },
            {
                "cell": "B4",
                "formula": "=SUM(B3:B3)",
                "number_format": "$#,##0.00",
                "bold": True
            }
        ]
    },
    "visible": True  # Set to False for headless operation
}

def test_edit_excel():
    """Test the edit-excel endpoint with sample metadata."""
    print(f"Testing Excel editing endpoint: {ENDPOINT}")
    
    try:
        # Make the POST request
        response = requests.post(
            ENDPOINT,
            json=SAMPLE_METADATA,
            headers={"Content-Type": "application/json"}
        )
        
        # Check if the request was successful
        if response.status_code == 200:
            result = response.json()
            print("✅ Success!")
            print(f"Message: {result.get('message')}")
            print(f"Modified sheets: {', '.join(result.get('modified_sheets', []))}")
            print(f"File saved to: {result.get('file_path')}")
        else:
            print(f"❌ Error: {response.status_code}")
            print(response.text)
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {str(e)}")

def verify_file_created():
    """Verify that the Excel file was created."""
    file_path = SAMPLE_METADATA["file_path"]
    if os.path.exists(file_path):
        print(f"\n✅ File created successfully at: {file_path}")
        print(f"File size: {os.path.getsize(file_path) / 1024:.2f} KB")
    else:
        print(f"\n❌ File not found at: {file_path}")

if __name__ == "__main__":
    print("=== Testing Excel Editing Endpoint ===")
    test_edit_excel()
    verify_file_created()
    print("\nTest completed!")