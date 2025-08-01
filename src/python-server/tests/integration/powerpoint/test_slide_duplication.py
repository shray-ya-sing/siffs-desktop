import os
import logging
import sys
import json
from pathlib import Path
from ai_services.tools.read_write_functions.powerpoint.powerpoint_edit_tools import parse_markdown_powerpoint_data
from powerpoint.editing.powerpoint_writer import PowerPointWriter

# Set up logging for debugging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

print("="*80)
print("SLIDE DUPLICATION TEST SCRIPT")
print("="*80)

# Test setup
pptx_path = "test_integration.pptx"  # Path to the test PowerPoint file

# Verify the PowerPoint file exists
if not os.path.exists(pptx_path):
    print(f"ERROR: PowerPoint file '{pptx_path}' not found!")
    print("Available PowerPoint files:")
    for file in Path(".").glob("*.pptx"):
        print(f"  - {file.name}")
    sys.exit(1)

print(f"Using PowerPoint file: {pptx_path}")
print()

# Test 1: Simple slide duplication
print("Test 1: Simple slide duplication (duplicate slide 1)")
print("-" * 50)

# Mock LLM response data with slide duplication command
# This simulates what the LLM would generate for slide duplication
llm_metadata_test1 = """slide_number: duplicate_slide:1"""

print(f"LLM Metadata Input: {repr(llm_metadata_test1)}")
print()

# Parse the metadata using existing function
print("Step 1: Parsing LLM metadata...")
slide_data_test1 = parse_markdown_powerpoint_data(llm_metadata_test1)
if not slide_data_test1:
    logger.error("Test 1 parsing failed. No slide data available.")
else:
    print(f"Parsed slide data: {json.dumps(slide_data_test1, indent=2)}")
    print()

    # Initialize the PowerPoint writer
    print("Step 2: Initializing PowerPoint writer...")
    ppt_writer = PowerPointWriter()
    print()

    # Write to PowerPoint - duplicate the slide
    print("Step 3: Executing slide duplication...")
    try:
        success, updated_shapes = ppt_writer.write_to_existing(slide_data_test1, pptx_path)
        if success:
            print(f"✅ Test 1 PASSED: Slide duplication completed successfully!")
            print(f"Updated shapes: {json.dumps(updated_shapes, indent=2)}")
        else:
            print("❌ Test 1 FAILED: Slide duplication failed.")
    except Exception as e:
        print(f"❌ Test 1 ERROR: {e}")
        logger.exception("Detailed error information:")

print()
print("="*80)

# Test 2: Slide duplication with target position
print("Test 2: Slide duplication with target position (duplicate slide 1 to position 3)")
print("-" * 70)

# This should duplicate slide 1 and place it at position 3
llm_metadata_test2 = """slide_number: slide3
slide_number: duplicate_slide:1"""

print(f"LLM Metadata Input: {repr(llm_metadata_test2)}")
print()

# Parse the metadata
print("Step 1: Parsing LLM metadata...")
slide_data_test2 = parse_markdown_powerpoint_data(llm_metadata_test2)
if not slide_data_test2:
    logger.error("Test 2 parsing failed. No slide data available.")
else:
    print(f"Parsed slide data: {json.dumps(slide_data_test2, indent=2)}")
    print()

    # Execute the duplication
    print("Step 2: Executing slide duplication with target position...")
    try:
        success, updated_shapes = ppt_writer.write_to_existing(slide_data_test2, pptx_path)
        if success:
            print(f"✅ Test 2 PASSED: Slide duplication with target position completed successfully!")
            print(f"Updated shapes: {json.dumps(updated_shapes, indent=2)}")
        else:
            print("❌ Test 2 FAILED: Slide duplication with target position failed.")
    except Exception as e:
        print(f"❌ Test 2 ERROR: {e}")
        logger.exception("Detailed error information:")

print()
print("="*80)

# Test 3: Mixed operations - duplicate slide and add content
print("Test 3: Mixed operations - duplicate slide 2 and add new content")
print("-" * 60)

# This should duplicate slide 2 and also add a new text box to a regular slide
llm_metadata_test3 = """slide_number: duplicate_slide:2

slide_number: slide1 | shape_name="Test Text Box", geom="textbox", left=50, top=300, width=200, height=100, text="This is a test text box added after duplication", font_size=12, font_name="Arial", font_color="#FF0000"""

print(f"LLM Metadata Input: {repr(llm_metadata_test3)}")
print()

# Parse the metadata
print("Step 1: Parsing LLM metadata...")
slide_data_test3 = parse_markdown_powerpoint_data(llm_metadata_test3)
if not slide_data_test3:
    logger.error("Test 3 parsing failed. No slide data available.")
else:
    print(f"Parsed slide data: {json.dumps(slide_data_test3, indent=2)}")
    print()

    # Execute the mixed operations
    print("Step 2: Executing mixed operations...")
    try:
        success, updated_shapes = ppt_writer.write_to_existing(slide_data_test3, pptx_path)
        if success:
            print(f"✅ Test 3 PASSED: Mixed operations completed successfully!")
            print(f"Updated shapes: {json.dumps(updated_shapes, indent=2)}")
        else:
            print("❌ Test 3 FAILED: Mixed operations failed.")
    except Exception as e:
        print(f"❌ Test 3 ERROR: {e}")
        logger.exception("Detailed error information:")

print()
print("="*80)
print("TEST SUMMARY")
print("="*80)
print("All tests completed. PowerPoint presentation is left open for inspection.")
print(f"Check the file: {pptx_path}")
print()
print("Expected results:")
print("- Test 1: Should have duplicated slide 1 and added it at the end")
print("- Test 2: Should have duplicated slide 1 and placed it at position 3")
print("- Test 3: Should have duplicated slide 2 and added a red text box to slide 1")
print()
print("PowerPoint application is intentionally left open for manual inspection.")
print("Close PowerPoint manually when finished inspecting.")

# Keep the script running to maintain the PowerPoint session
print("\nPress Ctrl+C to exit this script (PowerPoint will remain open)")
try:
    while True:
        import time
        time.sleep(1)
except KeyboardInterrupt:
    print("\nScript terminated. PowerPoint application remains open for inspection.")
