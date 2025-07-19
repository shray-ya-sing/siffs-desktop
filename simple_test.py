#!/usr/bin/env python3

import os
import sys

# Add the Python server to the path
sys.path.insert(0, os.path.join(os.getcwd(), 'src', 'python-server'))

print("Testing PowerPoint metadata extraction...")

try:
    # Import the extractor
    from powerpoint.metadata.extraction.pptx_metadata_extractor import PowerPointMetadataExtractor
    print("✓ Successfully imported PowerPointMetadataExtractor")
    
    # Create an extractor instance
    extractor = PowerPointMetadataExtractor()
    print("✓ Successfully created extractor instance")
    
    # Test file path
    file_path = r'C:\Users\shrey\AppData\Local\Temp\tmp_2024.10.27 Project Core - Valuation Analysis_v22_638j0a3p.pptx'
    
    if os.path.exists(file_path):
        print(f"✓ Found test file: {os.path.basename(file_path)}")
        
        # Extract metadata
        print("Extracting metadata...")
        metadata = extractor.extract_presentation_metadata(file_path)
        print(f"✓ Successfully extracted metadata")
        
        # Basic validation
        total_slides = metadata.get('totalSlides', 0)
        slides = metadata.get('slides', [])
        print(f"✓ Found {total_slides} slides in metadata")
        print(f"✓ Slides data contains {len(slides)} slide objects")
        
        # Check if we have the 5th slide we created
        if len(slides) >= 5:
            slide_5 = slides[4]  # 0-indexed
            print(f"✓ Slide 5 exists with {len(slide_5.get('shapes', []))} shapes")
            
            # Check if it has a table (which we created)
            has_table = False
            for shape in slide_5.get('shapes', []):
                if 'TABLE' in str(shape.get('shapeType', '')):
                    has_table = True
                    break
            
            if has_table:
                print("✓ Slide 5 contains a table as expected")
            else:
                print("⚠ Slide 5 does not contain a table")
        else:
            print("⚠ Slide 5 not found - may not have been properly created")
        
        # Check for errors
        error_count = 0
        total_shapes = 0
        
        for slide in slides:
            for shape in slide.get('shapes', []):
                total_shapes += 1
                if 'error' in str(shape).lower():
                    error_count += 1
        
        print(f"✓ Processed {total_shapes} shapes total")
        if error_count > 0:
            print(f"⚠ Found {error_count} shapes with errors")
        else:
            print("✓ No shape extraction errors detected")
            
    else:
        print(f"✗ Test file not found: {file_path}")
        
except ImportError as e:
    print(f"✗ Import error: {e}")
except Exception as e:
    print(f"✗ Extraction error: {e}")
    import traceback
    traceback.print_exc()

print("Test completed.")
