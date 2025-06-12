# test_reject_edit.py
import requests
import json
import sys
from pathlib import Path
from typing import List, Dict, Any

# Add project root to path to allow imports
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.append(str(project_root))

# Test configuration
BASE_URL = "http://127.0.0.1:3001"  # Update with your server URL
EDIT_ENDPOINT = f"{BASE_URL}/api/excel/edit-excel"
REJECT_ENDPOINT = f"{BASE_URL}/api/excel/edits/reject"

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
                "fill_color": "#2D5A27",
                "wrap_text": True
            },
        ]
    },
    "visible": True
}

def make_edit() -> Dict[str, Any]:
    """Make an edit to the Excel file and return the response."""
    print(f"\nMaking edit to Excel file...")
    try:
        response = requests.post(
            EDIT_ENDPOINT,
            json=SAMPLE_METADATA,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Edit request failed: {str(e)}")
        if hasattr(e, 'response') and e.response:
            print(f"Response: {e.response.text}")
        raise

def reject_edits(edit_ids: List[str]) -> Dict[str, Any]:
    """Reject the specified edit IDs."""
    if not edit_ids:
        print("No edit IDs to reject")
        return {}

    request_body = {"edit_ids": edit_ids}
    print(f"Sending request to {REJECT_ENDPOINT} with body:")
    print(json.dumps(request_body, indent=2))
        
    print(f"\nRejecting {len(edit_ids)} edits...")
    try:
        response = requests.post(
            REJECT_ENDPOINT,
            json=request_body,
            headers={"Content-Type": "application/json"}
        )
        # Print the response for debugging
        print(f"\nResponse status: {response.status_code}")
        print("Response body:")
        print(json.dumps(response.json(), indent=2) if response.text else "No response body")
        
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Reject edits request failed: {str(e)}")
        if hasattr(e, 'response') and e.response:
            print(f"Response: {e.response.text}")
        raise

def extract_edit_ids(response_data: Dict[str, Any]) -> List[str]:
    """Extract edit IDs from the edit response."""
    edit_ids = []
    pending_edits = response_data.get('request_pending_edits', [])
    
    for edit in pending_edits:
        if 'edit_id' in edit:
            edit_ids.append(edit['edit_id'])
    
    return edit_ids

def print_summary(operation: str, data: Dict[str, Any]):
    """Print a summary of the operation results."""
    print(f"\n=== {operation.upper()} SUMMARY ===")
    if operation == 'edit':
        print(f"Status: {data.get('status', 'unknown')}")
        print(f"Message: {data.get('message', 'No message')}")
        print(f"Modified sheets: {', '.join(data.get('modified_sheets', []))}")
        print(f"File path: {data.get('file_path')}")
    elif operation == 'reject':
        if data.get('success', False):
            print("✅ Successfully rejected edits")
            print(f"Rejected count: {data.get('rejected_count', 0)}")
            if data.get('failed_ids'):
                print(f"Failed IDs: {data.get('failed_ids')}")
        else:
            print("❌ Failed to reject edits")
            print(f"Error: {data.get('error', 'Unknown error')}")
    print("=" * 30)

def main():
    print("=== Starting Excel Edit & Reject Test ===")
    
    try:
        # Step 1: Make an edit to get edit IDs
        print("\n1. Making test edit to get edit IDs...")
        edit_response = make_edit()
        print_summary('edit', edit_response)
        
        # Step 2: Extract edit IDs from the response
        edit_ids = extract_edit_ids(edit_response)
        if not edit_ids:
            print("❌ No edit IDs found in the response")
            return
            
        print(f"Extracted {len(edit_ids)} edit IDs: {edit_ids}")
        
        # Step 3: Reject the edits
        print("\n2. Rejecting the edits...")
        reject_response = reject_edits(edit_ids)
        print_summary('reject', reject_response)
        
        print("\n✅ Test completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())