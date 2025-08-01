#!/usr/bin/env python3
"""
Comprehensive test script to verify PowerPoint writer and cache manager integration:
1. Create blank PPTX file
2. Extract metadata mirroring app logic
3. Edit by adding slides and shapes  
4. Update cache using cache manager
5. Verify updates are properly reflected in cached JSON
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
import tempfile

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from pptx import Presentation
    PPTX_AVAILABLE = True
except ImportError:
    PPTX_AVAILABLE = False
    print("Warning: python-pptx not available")

from powerpoint.editing.powerpoint_writer import PowerPointWriter
from powerpoint.metadata.extraction.pptx_metadata_extractor import PowerPointMetadataExtractor
from ai_services.tools.read_write_functions.powerpoint.powerpoint_edit_tools import update_powerpoint_cache

def setup_mock_cache(test_file_path: str, workspace_path: str):
    """Set up a mock cache for testing"""
    python_server_dir = Path(__file__).parent.absolute()
    cache_dir = python_server_dir / "metadata" / "_cache"
    mappings_dir = python_server_dir / "metadata" / "__cache"
    
    # Create directories if they don't exist
    cache_dir.mkdir(parents=True, exist_ok=True)
    mappings_dir.mkdir(parents=True, exist_ok=True)
    
    cache_file = cache_dir / "powerpoint_metadata_hotcache.json"
    mappings_file = mappings_dir / "files_mappings.json"
    
    # Create mock cache data
    mock_cache = {
        "test_presentation": {
            "file_path": test_file_path,
            "workspace_path": workspace_path,
            "presentation_name": Path(test_file_path).name,
            "slides": [
                {
                    "slideNumber": 1,
                    "slideId": "slide_1",
                    "name": "Slide 1",
                    "layoutName": "Title and Content",
                    "shapes": [],
                    "notes": {"hasNotes": False},
                    "comments": []
                }
            ],
            "lastModified": datetime.now().isoformat(),
            "created": datetime.now().isoformat()
        }
    }
    
    # Create mock file mappings
    mock_mappings = {
        workspace_path: test_file_path
    }
    
    # Write mock data to files
    with open(cache_file, 'w', encoding='utf-8') as f:
        json.dump(mock_cache, f, indent=2, ensure_ascii=False)
    
    with open(mappings_file, 'w', encoding='utf-8') as f:
        json.dump(mock_mappings, f, indent=2, ensure_ascii=False)
    
    return cache_file, mappings_file

def read_cache(cache_file: Path) -> dict:
    """Read cache data from file"""
    try:
        with open(cache_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

def create_blank_powerpoint(file_path: str) -> bool:
    """Create a blank PowerPoint file using python-pptx"""
    if not PPTX_AVAILABLE:
        print("✗ python-pptx not available, cannot create blank PowerPoint")
        return False
    
    try:
        # Create a blank presentation
        prs = Presentation()
        prs.save(file_path)
        print(f"✓ Created blank PowerPoint: {file_path}")
        return True
    except Exception as e:
        print(f"✗ Failed to create blank PowerPoint: {str(e)}")
        return False

def setup_cache_directories():
    """Set up cache directories for the test"""
    python_server_dir = Path(__file__).parent.absolute()
    cache_dir = python_server_dir / "metadata" / "_cache"
    mappings_dir = python_server_dir / "metadata" / "__cache"
    
    # Create directories if they don't exist
    cache_dir.mkdir(parents=True, exist_ok=True)
    mappings_dir.mkdir(parents=True, exist_ok=True)
    
    cache_file = cache_dir / "powerpoint_metadata_hotcache.json"
    mappings_file = mappings_dir / "files_mappings.json"
    
    return cache_file, mappings_file

def test_complete_integration():
    """Complete integration test following the 5-step process"""
    print("=== PowerPoint Writer & Cache Manager Integration Test ===")
    print("Following the 5-step process:")
    print("1. Create blank PPTX")
    print("2. Extract metadata mirroring app logic")
    print("3. Edit by adding slides and shapes")
    print("4. Update cache using cache manager")
    print("5. Verify updates in cached JSON")
    print()
    
    test_file = "test_integration.pptx"
    workspace_path = f"test_workspace/{test_file}"
    
    try:
        # Step 1: Create blank PPTX
        print("--- STEP 1: Create blank PPTX ---")
        if not create_blank_powerpoint(test_file):
            return
        
        # Step 2: Extract metadata mirroring app logic
        print("\n--- STEP 2: Extract metadata mirroring app logic ---")
        
        # Set up cache directories
        cache_file, mappings_file = setup_cache_directories()
        
        # Create file mappings (mirrors app logic)
        mappings = {workspace_path: os.path.abspath(test_file)}
        with open(mappings_file, 'w', encoding='utf-8') as f:
            json.dump(mappings, f, indent=2)
        print(f"✓ Created file mappings: {mappings_file}")
        
        # Extract metadata using the PowerPoint metadata extractor
        extractor = PowerPointMetadataExtractor()
        metadata = extractor.extract_presentation_metadata(test_file)
        print(f"✓ Extracted metadata: {metadata['totalSlides']} slides, {len(metadata['slides'])} slide details")
        
        # Create cache entry (mirrors app cache storage logic)
        cache_key = f"presentation_{hash(workspace_path)}"
        cache_data = {
            cache_key: {
                "file_path": os.path.abspath(test_file),
                "workspace_path": workspace_path,
                "presentation_name": Path(test_file).name,
                "extractedAt": metadata["extractedAt"],
                "totalSlides": metadata["totalSlides"],
                "slides": metadata["slides"],
                "slideLayouts": metadata.get("slideLayouts", []),
                "coreProperties": metadata.get("coreProperties", {}),
                "slideSize": metadata.get("slideSize", {}),
                "lastModified": datetime.now().isoformat(),
                "created": datetime.now().isoformat()
            }
        }
        
        # Write to cache file
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, indent=2, ensure_ascii=False)
        print(f"✓ Created cache file: {cache_file}")
        
        # Verify initial cache state
        initial_cache = read_cache(cache_file)
        presentation_data = initial_cache.get(cache_key, {})
        initial_slides = presentation_data.get("slides", [])
        print(f"✓ Initial cache state: {len(initial_slides)} slides")
        
        if initial_slides:
            initial_shapes = initial_slides[0].get("shapes", [])
            print(f"✓ Slide 1 has {len(initial_shapes)} shapes initially")
        
        # Step 3: Edit by adding slides and shapes
        print("\n--- STEP 3: Edit by adding slides and shapes ---")
        
        writer = PowerPointWriter()
        
        # Add shapes to existing slide
        slide_data = {
            "1": {
                "Title Shape": {
                    "type": "textbox",
                    "left": 100,
                    "top": 50,
                    "width": 500,
                    "height": 80,
                    "text": "Integration Test Title"
                },
                "Content Shape": {
                    "type": "textbox",
                    "left": 100,
                    "top": 150,
                    "width": 500,
                    "height": 100,
                    "text": "This is content added by the integration test"
                }
            }
        }
        
        success1, updated_shapes1 = writer.write_to_existing(slide_data, test_file)
        print(f"✓ Added shapes to slide 1: Success={success1}, {len(updated_shapes1)} shapes updated")
        
        # Add a new slide with shapes
        new_slide_data = {
            "2": {
                "Slide 2 Title": {
                    "type": "textbox",
                    "left": 100,
                    "top": 50,
                    "width": 500,
                    "height": 80,
                    "text": "Second Slide Title"
                },
                "Slide 2 Content": {
                    "type": "textbox",
                    "left": 100,
                    "top": 150,
                    "width": 500,
                    "height": 120,
                    "text": "Content for the second slide added by integration test"
                }
            }
        }
        
        success2, updated_shapes2 = writer.write_to_existing(new_slide_data, test_file)
        print(f"✓ Added new slide 2: Success={success2}, {len(updated_shapes2)} shapes updated")
        
        all_updated_shapes = updated_shapes1 + updated_shapes2
        print(f"✓ Total shapes updated: {len(all_updated_shapes)}")
        
        # Print shape details
        print("Updated shapes details:")
        for shape in all_updated_shapes:
            print(f"  - {shape.get('shape_name')} on slide {shape.get('slide_number')}")
        
        # Step 4: Update cache using cache manager
        print("\n--- STEP 4: Update cache using cache manager ---")
        
        cache_success = update_powerpoint_cache(workspace_path, all_updated_shapes)
        print(f"✓ Cache manager result: Success={cache_success}")
        
        # Step 5: Verify updates in cached JSON
        print("\n--- STEP 5: Verify updates in cached JSON ---")
        
        final_cache = read_cache(cache_file)
        final_presentation = final_cache.get(cache_key, {})
        final_slides = final_presentation.get("slides", [])
        
        print(f"✓ Final cache state: {len(final_slides)} slides")
        
        # Verify slide 1 shapes
        if len(final_slides) >= 1:
            slide1_shapes = final_slides[0].get("shapes", [])
            print(f"✓ Slide 1 now has {len(slide1_shapes)} shapes")
            
            slide1_shape_names = [s.get('name') for s in slide1_shapes]
            expected_slide1_shapes = ["Title Shape", "Content Shape"]
            
            found_shapes = [name for name in expected_slide1_shapes if name in slide1_shape_names]
            print(f"✓ Found shapes on slide 1: {found_shapes}")
            
            if len(found_shapes) == len(expected_slide1_shapes):
                print("✓ SUCCESS: All expected shapes found on slide 1")
            else:
                missing = [name for name in expected_slide1_shapes if name not in found_shapes]
                print(f"✗ PARTIAL: Missing shapes on slide 1: {missing}")
        
        # Verify slide 2 was created
        if len(final_slides) >= 2:
            slide2_shapes = final_slides[1].get("shapes", [])
            print(f"✓ Slide 2 created with {len(slide2_shapes)} shapes")
            
            slide2_shape_names = [s.get('name') for s in slide2_shapes]
            expected_slide2_shapes = ["Slide 2 Title", "Slide 2 Content"]
            
            found_shapes_s2 = [name for name in expected_slide2_shapes if name in slide2_shape_names]
            print(f"✓ Found shapes on slide 2: {found_shapes_s2}")
            
            if len(found_shapes_s2) == len(expected_slide2_shapes):
                print("✓ SUCCESS: All expected shapes found on slide 2")
            else:
                missing_s2 = [name for name in expected_slide2_shapes if name not in found_shapes_s2]
                print(f"✗ PARTIAL: Missing shapes on slide 2: {missing_s2}")
        else:
            print("✗ FAILED: Slide 2 was not created in cache")
        
        # Final verification
        if len(final_slides) >= 2:
            slide1_ok = len(final_slides[0].get("shapes", [])) >= 2
            slide2_ok = len(final_slides[1].get("shapes", [])) >= 2
            
            if slide1_ok and slide2_ok:
                print("\n🎉 OVERALL SUCCESS: PowerPoint writer and cache manager integration works correctly!")
                print("   - Blank PPTX created ✓")
                print("   - Metadata extracted ✓")
                print("   - Slides and shapes added ✓")
                print("   - Cache properly updated ✓")
                print("   - Updates reflected in JSON ✓")
            else:
                print("\n⚠️  PARTIAL SUCCESS: Some issues found in integration")
        else:
            print("\n❌ FAILED: Integration test did not complete successfully")
            
    except Exception as e:
        print(f"✗ ERROR during integration test: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        # Clean up
        cleanup_files = [test_file, cache_file, mappings_file]
        for file_path in cleanup_files:
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    print(f"Cleaned up {file_path}")
                except:
                    pass

def test_cache_update_modify_objects():
    """Test that cache is updated when modifying objects on existing slides"""
    print("\n=== Testing Cache Update for Modified Objects ===")
    
    test_file = "test_cache_modify.pptx"
    
    try:
        writer = PowerPointWriter()
        
        # Create initial slide with one shape
        initial_data = [{
            'slideNumber': 1,
            'shapes': [{
                'name': 'Original Shape',
                'type': 'textbox',
                'left': 100,
                'top': 100,
                'width': 300,
                'height': 80,
                'text': 'Original text content'
            }]
        }]
        
        print("Creating initial slide with one shape...")
        result = writer.write_shapes(test_file, initial_data)
        print(f"Initial creation result: {result}")
        
        # Check initial cache
        initial_shape_count = 0
        if hasattr(writer, 'cached_metadata') and writer.cached_metadata:
            slides = writer.cached_metadata.get('slides', [])
            if slides:
                initial_shape_count = len(slides[0].get('shapes', []))
                print(f"Initial cache: Slide 1 has {initial_shape_count} shapes")
        
        # Add another shape to the same slide
        print("\nAdding second shape to existing slide...")
        modified_data = [{
            'slideNumber': 1,
            'shapes': [{
                'name': 'Second Shape',
                'type': 'textbox',
                'left': 100,
                'top': 200,
                'width': 350,
                'height': 90,
                'text': 'Second shape added to slide'
            }]
        }]
        
        result = writer.write_shapes(test_file, modified_data)
        print(f"Shape addition result: {result}")
        
        # Check updated cache
        if hasattr(writer, 'cached_metadata') and writer.cached_metadata:
            slides = writer.cached_metadata.get('slides', [])
            if slides:
                updated_shape_count = len(slides[0].get('shapes', []))
                print(f"Updated cache: Slide 1 has {updated_shape_count} shapes")
                
                print("Shapes in cache:")
                for shape in slides[0].get('shapes', []):
                    print(f"  - {shape.get('name', 'Unnamed')}: '{shape.get('text', 'No text')[:30]}...'")
                
                if updated_shape_count > initial_shape_count:
                    print(f"✓ SUCCESS: Cache updated with new shape ({initial_shape_count} -> {updated_shape_count} shapes)")
                else:
                    print(f"✗ FAILED: Cache not updated properly ({initial_shape_count} -> {updated_shape_count} shapes)")
            else:
                print("✗ FAILED: No slides found in cache")
        else:
            print("✗ FAILED: No cache found")
            
    except Exception as e:
        print(f"✗ ERROR during test: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        # Clean up
        if os.path.exists(test_file):
            try:
                os.remove(test_file)
                print(f"Cleaned up {test_file}")
            except:
                print(f"Could not clean up {test_file}")

if __name__ == "__main__":
    print("Testing PowerPoint Writer & Cache Manager Integration")
    print("=" * 60)
    
    test_complete_integration()
    
    print("\n" + "=" * 60)
print("Integration testing completed")

# Now read and verify the updated cache directly
print("\n--- VERIFYING UPDATED CACHE CONTENT ---")
cache_data = read_cache(cache_file)
if cache_data:
    print("Cache content correctly loaded:")
    for presentation_key, presentation in cache_data.items():
        print(f"Presentation: {presentation_key} - {presentation.get('presentation_name')}")
        slides = presentation.get('slides', [])
        for slide in slides:
            slide_number = slide.get('slideNumber')
            shape_count = len(slide.get('shapes', []))
            print(f"  Slide {slide_number}: {shape_count} shapes")
            for shape in slide.get('shapes', []):
                print(f"    - Shape Name: {shape.get('name')}, Last Modified: {shape.get('lastModified')}")
else:
    print("✗ ERROR: Unable to load updated cache content")
