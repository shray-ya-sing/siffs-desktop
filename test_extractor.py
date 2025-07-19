#!/usr/bin/env python3

import sys
import os
sys.path.append('src/python-server')

try:
    from powerpoint.metadata.extraction.pptx_metadata_extractor import PowerPointMetadataExtractor
    import json

    # Test the most recent file
    file_path = r'C:\Users\shrey\AppData\Local\Temp\tmp_2024.10.27 Project Core - Valuation Analysis_v22_638j0a3p.pptx'
    
    if not os.path.exists(file_path):
        print(f'File not found: {file_path}')
        exit(1)

    print('Testing improved metadata extractor...')
    extractor = PowerPointMetadataExtractor()
    metadata = extractor.extract_presentation_metadata(file_path)

    print(f'Total slides: {metadata.get("totalSlides", 0)}')
    print('Slide details:')
    for slide in metadata.get('slides', []):
        slide_num = slide.get('slideNumber', 'Unknown')
        shapes = len(slide.get('shapes', []))
        print(f'  Slide {slide_num}: {shapes} shapes')

    # Check for errors in shapes
    print('\nChecking for extraction errors...')
    errors_found = 0
    total_shapes = 0
    color_errors = 0
    
    for slide in metadata.get('slides', []):
        for shape in slide.get('shapes', []):
            total_shapes += 1
            if 'error' in str(shape):
                errors_found += 1
            
            # Check for color extraction errors
            if 'textContent' in shape and 'paragraphs' in shape['textContent']:
                for para in shape['textContent']['paragraphs']:
                    for run in para.get('runs', []):
                        font = run.get('font', {})
                        if 'color' in font and 'error' in str(font['color']):
                            color_errors += 1

    print(f'Total shapes processed: {total_shapes}')
    print(f'Shapes with errors: {errors_found}')
    print(f'Font color extraction errors: {color_errors}')
    
    # Check if slide 5 exists (the one we created)
    slide_5 = None
    for slide in metadata.get('slides', []):
        if slide.get('slideNumber') == 5:
            slide_5 = slide
            break
    
    if slide_5:
        print(f'\nSlide 5 found with {len(slide_5.get("shapes", []))} shapes')
        for i, shape in enumerate(slide_5.get('shapes', [])):
            name = shape.get('name', 'Unknown')
            shape_type = shape.get('shapeType', 'Unknown')
            print(f'  Shape {i}: {name} ({shape_type})')
    else:
        print('\nSlide 5 not found in metadata')

except Exception as e:
    print(f'ERROR: {str(e)}')
    import traceback
    traceback.print_exc()
