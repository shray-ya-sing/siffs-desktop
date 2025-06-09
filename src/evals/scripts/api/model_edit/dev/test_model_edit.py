import requests
import json
import os
from typing import Dict, Any

# Configuration
BASE_URL = "http://127.0.0.1:3001/api"  # Update if your server is running on a different port
EXCEL_FILE_PATH = r"C:\Users\shrey\OneDrive\Desktop\docs\test\test_model_Alibaba_IPO(shorter)_llm.xlsx"

# Sample metadata chunk from the Excel file
SAMPLE_CHUNK_MARKDOWN = """
# Chunk: 
Workbook Name: test_model_Alibaba_IPO(shorter)_llm.xlsx 
Sheet Name: Quarterly IS
Rows: 1-10 (10 rows) | Columns: 16
| Row | A | B | C | D | E | F | G | H | I | J | K | L | M | N | O | P |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | A1, v="#REF!", f="=#REF!", fmt=[bold,fill:#00B0F0], type=f | B1, fmt=[fill:#00B0F0] | C1, fmt=[fill:#00B0F0] | D1, fmt=[fill:#00B0F0] | E1, fmt=[fill:#00B0F0] | F1, fmt=[fill:#00B0F0] | G1, fmt=[fill:#00B0F0] | H1, fmt=[fill:#00B0F0] | I1, fmt=[fill:#00B0F0] | J1, fmt=[fill:#00B0F0] | K1, fmt=[fill:#00B0F0] | L1 | M1 | N1 | O1 | P1 |
| 2 | A2, v=Quarterly Income Statement, fmt=[fill:#00B0F0] | B2, fmt=[fill:#00B0F0] | C2, fmt=[fill:#00B0F0] | D2, fmt=[fill:#00B0F0] | E2, fmt=[fill:#00B0F0] | F2, fmt=[fill:#00B0F0] | G2, fmt=[fill:#00B0F0] | H2, fmt=[fill:#00B0F0] | I2, fmt=[fill:#00B0F0] | J2, fmt=[fill:#00B0F0] | K2, fmt=[fill:#00B0F0] | L2 | M2 | N2 | O2 | P2 |
| 3 | A3 | B3 | C3 | D3 | E3 | F3 | G3 | H3 | I3 | J3 | K3 | L3 | M3 | N3 | O3 | P3 |
| 4 | A4, fmt=[bold,color:#00B0F0] | B4 | C4, v=Quarter Ended, fmt=[bold,fill:#00B0F0] | D4, fmt=[bold,fill:#00B0F0] | E4, fmt=[bold,fill:#00B0F0] | F4, fmt=[bold,fill:#00B0F0] | G4, fmt=[bold,fill:#00B0F0] | H4, fmt=[bold,fill:#00B0F0] | I4, fmt=[bold,fill:#00B0F0] | J4, fmt=[bold,fill:#00B0F0] | K4 | L4 | M4 | N4 | O4 | P4 |
| 5 | A5 | B5, fmt=[bold,color:#00B0F0] | C5, v=2012-06-30T00:00:00, fmt=[bold,fill:#00B0F0,fmt:[$-409]d\-], type=d | D5, v=2012-09-30T00:00:00, fmt=[bold,fill:#00B0F0,fmt:[$-409]d\-], type=d | E5, v=2012-12-31T00:00:00, fmt=[bold,fill:#00B0F0,fmt:[$-409]d\-], type=d | F5, v=2013-03-31T00:00:00, fmt=[bold,fill:#00B0F0,fmt:[$-409]d\-], type=d | G5, v=2013-06-30T00:00:00, fmt=[bold,fill:#00B0F0,fmt:[$-409]d\-], type=d | H5, v=2013-09-30T00:00:00, fmt=[bold,fill:#00B0F0,fmt:[$-409]d\-], type=d | I5, v=2013-12-31T00:00:00, fmt=[bold,fill:#00B0F0,fmt:[$-409]d\-], type=d | J5, v=2014-03-31T00:00:00, fmt=[bold,fill:#00B0F0,fmt:[$-409]d\-], type=d | K5 | L5 | M5 | N5 | O5 | P5 |
| 6 | A6 | B6, v="(RMB in Million Except Per Share Amounts)", fmt=[bold] | C6, v=2012, fmt=[bold] | D6, v=2012, fmt=[bold] | E6, v=2012, fmt=[bold] | F6, v=2013, fmt=[bold] | G6, v=2013, fmt=[bold] | H6, v=2013, fmt=[bold] | I6, v=2013, fmt=[bold] | J6, v=2014, fmt=[bold] | K6 | L6 | M6 | N6 | O6 | P6 |
| 7 | A7 | B7 | C7 | D7 | E7 | F7 | G7 | H7 | I7 | J7 | K7 | L7 | M7 | N7 | O7 | P7 |
| 8 | A8 | B8, v=China commerce | C8, v=5601, deps=0→2, dept=[Quarterly IS!C12,Quarterly IS!C51], fmt=[color:#0070C0,fmt:_(* #,##0_] | D8, v=6152, deps=0→2, dept=[Quarterly IS!D51,Quarterly IS!D12], fmt=[color:#0070C0,fmt:_(* #,##0_] | E8, v=10172, deps=0→2, dept=[Quarterly IS!E12,Quarterly IS!E51], fmt=[color:#0070C0,fmt:_(* #,##0_] | F8, v=7242, deps=0→2, dept=[Quarterly IS!F12,Quarterly IS!F51], fmt=[color:#0070C0,fmt:_(* #,##0_] | G8, v=9193, deps=0→2, dept=[Quarterly IS!G51,Quarterly IS!G12], fmt=[color:#0070C0,fmt:_(* #,##0_] | H8, v=9213, deps=0→2, dept=[Quarterly IS!H12,Quarterly IS!H51], fmt=[color:#0070C0,fmt:_(* #,##0_] | I8, v=16761, deps=0→2, dept=[Quarterly IS!I51,Quarterly IS!I12], fmt=[color:#0070C0,fmt:_(* #,##0_] | J8, v=12570.75, f==J51, deps=1→1, prec=[Quarterly IS!J51], dept=[Quarterly IS!J12], fmt=[fmt:_(* #,##0_], type=f | K8 | L8 | M8 | N8 | O8 | P8 |
| 9 | A9 | B9, v=International commerce | C9, v=974, deps=0→2, dept=[Quarterly IS!C54,Quarterly IS!C12], fmt=[color:#0070C0,fmt:_(* #,##0_] | D9, v=1049, deps=0→2, dept=[Quarterly IS!D54,Quarterly IS!D12], fmt=[color:#0070C0,fmt:_(* #,##0_] | E9, v=1094, deps=0→2, dept=[Quarterly IS!E12,Quarterly IS!E54], fmt=[color:#0070C0,fmt:_(* #,##0_] | F9, v=1043, deps=0→2, dept=[Quarterly IS!F12,Quarterly IS!F54], fmt=[color:#0070C0,fmt:_(* #,##0_] | G9, v=1117, deps=0→2, dept=[Quarterly IS!G54,Quarterly IS!G12], fmt=[color:#0070C0,fmt:_(* #,##0_] | H9, v=1176, deps=0→2, dept=[Quarterly IS!H12,Quarterly IS!H54], fmt=[color:#0070C0,fmt:_(* #,##0_] | I9, v=1264, deps=0→2, dept=[Quarterly IS!I54,Quarterly IS!I12], fmt=[color:#0070C0,fmt:_(* #,##0_] | J9, v=1200.8, f==J54, deps=1→1, prec=[Quarterly IS!J54], dept=[Quarterly IS!J12], fmt=[fmt:_(* #,##0_], type=f | K9 | L9 | M9 | N9 | O9 | P9 |
| 10 | A10 | B10, v=Cloud computing and Internet infrastructure | C10, v=155, deps=0→2, dept=[Quarterly IS!C12,Quarterly IS!C57], fmt=[color:#0070C0,fmt:_(* #,##0_] | D10, v=164, deps=0→2, dept=[Quarterly IS!D12,Quarterly IS!D57], fmt=[color:#0070C0,fmt:_(* #,##0_] | E10, v=165, deps=0→2, dept=[Quarterly IS!E12,Quarterly IS!E57], fmt=[color:#0070C0,fmt:_(* #,##0_] | F10, v=166, deps=0→2, dept=[Quarterly IS!F12,Quarterly IS!F57], fmt=[color:#0070C0,fmt:_(* #,##0_] | G10, v=174, deps=0→2, dept=[Quarterly IS!G12,Quarterly IS!G57], fmt=[color:#0070C0,fmt:_(* #,##0_] | H10, v=190, deps=0→2, dept=[Quarterly IS!H12,Quarterly IS!H57], fmt=[color:#0070C0,fmt:_(* #,##0_] | I10, v=196, deps=0→2, dept=[Quarterly IS!I57,Quarterly IS!I12], fmt=[color:#0070C0,fmt:_(* #,##0_] | J10, v=197.96, f==J57, deps=1→1, prec=[Quarterly IS!J57], dept=[Quarterly IS!J12], fmt=[fmt:_(* #,##0_], type=f | K10 | L10 | M10 | N10 | O10 | P10 |
**Dependencies:** precedents:3, dependents:29, external:3
**Key Precedents:** Quarterly IS!J57, Quarterly IS!J54, Quarterly IS!J51
**Key Dependents:** Quarterly IS!C51, Quarterly IS!F54, Quarterly IS!I54, Quarterly IS!E51, Quarterly IS!G51
"""

SAMPLE_CHUNK = {
    "markdown": SAMPLE_CHUNK_MARKDOWN,
    "text": SAMPLE_CHUNK_MARKDOWN,
    "score": 1.0,
    "metadata": {
        "workbook": "test_model_Alibaba_IPO(shorter)_llm.xlsx",
        "sheet": "Quarterly IS",
        "rows": "1-10 (10 rows)",
        "columns": "16"
    },
    "chunk_index": 1
}

# User's edit request
USER_REQUEST = """
Can you help me update the Q2 2023 revenue numbers for our China commerce segment? 
I need to adjust the figures to reflect the latest sales data we just received. 
The current values for Q2 2023 (ending June 30, 2023) in column J look off compared to our internal reports. 
Also, please make sure the formatting stays consistent with the rest of the quarterly income statement, 
keeping the same number format and blue text color for these revenue line items.
"""

def test_edit_flow():
    headers = {
        'Content-Type': 'application/json'
    }
    
    # Step 1: Generate edit metadata
    print("Step 1: Generating edit metadata...")
    generate_url = f"{BASE_URL}/excel/generate-edit-metadata"
    payload = {
        "user_request": USER_REQUEST,
        "chunks": [SAMPLE_CHUNK],
        "chunk_limit": 1,
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 2000,
        "temperature": 0.3,
        "stream": False
    }
    
    try:
        # Generate metadata
        response = requests.post(generate_url, json=payload, headers=headers)
        response.raise_for_status()
        response_data = response.json()
        metadata_str = response_data.get('result', '')
        
        if not metadata_str:
            print("Error: Empty metadata string received")
            return False
            
        # Print first 200 chars of metadata
        print("✅ Successfully generated metadata")
        print(f"Metadata preview (first 200 chars): {metadata_str[:200]}...\n")
        
        # Step 2: Parse the metadata
        print("Step 2: Parsing metadata...")
        parse_url = f"{BASE_URL}/excel/parse-metadata"
        parse_payload = {
            "metadata": metadata_str,
            "strict": True
        }
        
        response = requests.post(parse_url, json=parse_payload, headers=headers)
        response.raise_for_status()
        parse_response = response.json()
        parsed_metadata = parse_response.get('data', {})
        
        if not parsed_metadata:
            print("Error: Failed to parse metadata")
            return False
            
        # Print first 200 chars of parsed metadata
        parsed_metadata_str = json.dumps(parsed_metadata)[:200]
        print("✅ Successfully parsed metadata")
        print(f"Parsed metadata preview (first 200 chars): {parsed_metadata_str}...\n")
        
        # Step 3: Apply the edit
        print("\nStep 3: Applying edit to Excel file...")
        edit_url = f"{BASE_URL}/excel/edit-excel"
        edit_payload = {
            "file_path": EXCEL_FILE_PATH,
            "metadata": parsed_metadata,
            "visible": True  # Set to False for headless operation
        }
        
        response = requests.post(edit_url, json=edit_payload, headers=headers)
        response.raise_for_status()
        
        result = response.json()
        if result.get('status') == 'success':
            print(f"✅ Successfully applied changes to {result.get('file_path')}")
            print(f"Modified sheets: {', '.join(result.get('modified_sheets', []))}")
            return True
        else:
            print(f"Error applying changes: {result.get('message', 'Unknown error')}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Error: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response status: {e.response.status_code}")
            print(f"Response body: {e.response.text}")
        return False

if __name__ == "__main__":
    print("Starting Excel Edit Flow Test")
    print("=" * 50)
    
    success = test_edit_flow()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ Test completed successfully!")
    else:
        print("❌ Test failed. Check the logs for details.")