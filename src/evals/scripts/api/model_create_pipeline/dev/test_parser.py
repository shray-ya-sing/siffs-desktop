# test_parse_metadata.py
import requests
import json
import pprint

# Configuration
BASE_URL = "http://127.0.0.1:3001"  # Update with your server URL
ENDPOINT = f"{BASE_URL}/api/excel/parse-metadata"

# The metadata to parse
METADATA = """
worksheet name= "Financial Analysis" | cell= "A1"; formula="Financial Analysis - Quarterly Forecast"; font_style="Arial"; font_size="14"; bold="true" | cell= "A2"; formula="($ in thousands)"; font_style="Arial"; font_size="10"; italic="true" | cell= "B3"; formula="Q1 2025"; font_style="Arial"; font_size="11"; bold="true"; horizontal_alignment="center" | cell= "C3"; formula="Q2 2025"; font_style="Arial"; font_size="11"; bold="true"; horizontal_alignment="center" | cell= "D3"; formula="Q3 2025"; font_style="Arial"; font_size="11"; bold="true"; horizontal_alignment="center" | cell= "E3"; formula="Q4 2025"; font_style="Arial"; font_size="11"; bold="true"; horizontal_alignment="center" | cell= "F3"; formula="Q1 2026"; font_style="Arial"; font_size="11"; bold="true"; horizontal_alignment="center" | cell= "G3"; formula="Q2 2026"; font_style="Arial"; font_size="11"; bold="true"; horizontal_alignment="center" | cell= "H3"; formula="Q3 2026"; font_style="Arial"; font_size="11"; bold="true"; horizontal_alignment="center" | cell= "I3"; formula="Q4 2026"; font_style="Arial"; font_size="11"; bold="true"; horizontal_alignment="center" | cell= "A5"; formula="Revenue"; font_style="Arial"; font_size="11"; bold="true"; fill_color="#E6F3FF" | cell= "B5"; formula="100"; number_format="#,##0" | cell= "C5"; formula="=B5*1.1"; number_format="#,##0" | cell= "D5"; formula="=C5*1.1"; number_format="#,##0" | cell= "E5"; formula="=D5*1.1"; number_format="#,##0" | cell= "F5"; formula="=E5*1.1"; number_format="#,##0" | cell= "G5"; formula="=F5*1.1"; number_format="#,##0" | cell= "H5"; formula="=G5*1.1"; number_format="#,##0" | cell= "I5"; formula="=H5*1.1"; number_format="#,##0"
"""

def test_parse_metadata(metadata: str, strict: bool = True):
    """Test the parse-metadata endpoint."""
    print(f"Testing metadata parsing endpoint: {ENDPOINT}")
    print(f"Strict mode: {strict}")
    
    try:
        # Prepare the request
        payload = {
            "metadata": metadata.strip(),
            "strict": strict
        }
        
        # Make the POST request
        response = requests.post(
            ENDPOINT,
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        # Process the response
        if response.status_code == 200:
            result = response.json()
            print("\n✅ Success!")
            print("Parsed metadata:")
            
            # Pretty print the JSON response
            pp = pprint.PrettyPrinter(indent=2)
            pp.pprint(result)
            
            # Save to file
            with open("parsed_metadata.json", "w") as f:
                json.dump(result, f, indent=2)
            print("\n✅ Full response saved to 'parsed_metadata.json'")
            
            return result
        else:
            print(f"\n❌ Error: {response.status_code}")
            print(response.text)
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Request failed: {str(e)}")
        return None

if __name__ == "__main__":
    print("=== Testing Metadata Parsing Endpoint ===")
    
    # Test with strict mode (default)
    print("\n--- Testing with strict mode ON ---")
    result_strict = test_parse_metadata(METADATA, strict=True)
    
    # Test with lenient mode
    print("\n--- Testing with strict mode OFF ---")
    result_lenient = test_parse_metadata(METADATA, strict=False)
    
    print("\nTest completed!")