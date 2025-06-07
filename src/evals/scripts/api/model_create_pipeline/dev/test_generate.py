# test_generate_metadata.py
import requests
import json
import os
from pathlib import Path

# Test configuration
BASE_URL = "http://127.0.0.1:3001"  # Update with your server URL
ENDPOINT = f"{BASE_URL}/api/excel/generate-metadata"

# Sample request for financial analysis
SAMPLE_REQUEST = {
    "user_request": """
    Create a financial analysis spreadsheet with the following:
    1. Quarterly revenue forecast for 2025-2026
    2. Starting revenue of $100,000 in Q1 2025 with 10% quarterly growth
    3. Expense categories: COGS (40% of revenue), Salaries ($20,000/quarter), Marketing (15% of revenue)
    4. Calculate Gross Profit, Operating Income, and Net Income (20% tax rate)
    5. Include appropriate number formatting and styling
    """,
    "model": "claude-sonnet-4-20250514",
    "max_tokens": 2000,
    "temperature": 0.3,
    "stream": False
}

def test_generate_metadata():
    """Test the generate-metadata endpoint with a financial analysis request."""
    print(f"Testing metadata generation endpoint: {ENDPOINT}")
    print("Sending request for financial analysis spreadsheet...")
    
    try:
        # Make the POST request
        response = requests.post(
            ENDPOINT,
            json=SAMPLE_REQUEST,
            headers={"Content-Type": "application/json"}
        )
        
        # Check if the request was successful
        if response.status_code == 200:
            result = response.json()
            print("✅ Success!")
            print(f"Model used: {result.get('model')}")
            
            # Save the generated metadata to a file
            output_file = "generated_metadata.txt"
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(result.get("result", ""))
                
            print(f"Generated metadata saved to: {os.path.abspath(output_file)}")
            print(f"Metadata length: {len(result.get('result', ''))} characters")
            
            return result.get("result")
        else:
            print(f"❌ Error: {response.status_code}")
            print(response.text)
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {str(e)}")
        return None

def test_streaming():
    """Test the streaming version of the endpoint."""
    print("\nTesting streaming metadata generation...")
    stream_request = SAMPLE_REQUEST.copy()
    stream_request["stream"] = True
    
    try:
        with requests.post(
            ENDPOINT,
            json=stream_request,
            headers={"Content-Type": "application/json"},
            stream=True
        ) as response:
            if response.status_code == 200:
                print("✅ Streaming started. Receiving chunks...")
                output_file = "streamed_metadata.txt"
                with open(output_file, "w", encoding="utf-8") as f:
                    for chunk in response.iter_lines():
                        if chunk:
                            chunk_str = chunk.decode('utf-8')
                            f.write(chunk_str + "\n")
                            print(".", end="", flush=True)
                
                print(f"\n✅ Streaming completed. Data saved to: {os.path.abspath(output_file)}")
            else:
                print(f"❌ Error: {response.status_code}")
                print(response.text)
                
    except Exception as e:
        print(f"❌ Streaming test failed: {str(e)}")

if __name__ == "__main__":
    print("=== Testing Metadata Generation Endpoint ===")
    print("Testing non-streaming request...")
    metadata = test_generate_metadata()
    
    print("\n=== Testing Streaming Request ===")
    test_streaming()
    
    print("\nTest completed!")