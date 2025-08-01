#!/usr/bin/env python3
"""
Test to verify cache updates work correctly when PowerPoint objects are modified
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from pptx import Presentation
    PPTX_AVAILABLE = True
except ImportError:
    PPTX_AVAILABLE = False

from powerpoint.editing.powerpoint_writer import PowerPointWriter
from powerpoint.metadata.extraction.pptx_metadata_extractor import PowerPointMetadataExtractor
from ai_services.tools.read_write_functions.powerpoint.powerpoint_edit_tools import update_powerpoint_cache

def test_cache_verification():
    """Test that verifies cache content is correctly updated"""
    print("=== Cache Verification Test ===")
    
    if not PPTX_AVAILABLE:
        print("❌ python-pptx not available, skipping test")
        return
    
    test_file = "cache_verification_test.pptx"
    workspace_path = f"test_workspace/{test_file}"
    
    # Set up cache directories using absolute paths to match what cache manager expects
    python_server_dir = Path.cwd()  # Use current working directory (python-server)
    cache_dir = python_server_dir / "metadata" / "_cache"
    mappings_dir = python_server_dir / "metadata" / "__cache"
    
    cache_dir.mkdir(parents=True, exist_ok=True)
    mappings_dir.mkdir(parents=True, exist_ok=True)
    
    cache_file = cache_dir / "powerpoint_metadata_hotcache.json"
    mappings_file = mappings_dir / "files_mappings.json"
    
    print(f"📁 Cache file path: {cache_file.absolute()}")
    print(f"📁 Mappings file path: {mappings_file.absolute()}")
    
    try:
        # Step 1: Create blank PPTX
        print("\n1️⃣ Creating blank PowerPoint...")
        prs = Presentation()
        prs.save(test_file)
        print(f"✅ Created: {test_file}")
        
        # Step 2: Set up file mappings in both locations
        print("\n2️⃣ Setting up file mappings...")
        mappings = {workspace_path: os.path.abspath(test_file)}
        
        # Create mappings in our location
        with open(mappings_file, 'w', encoding='utf-8') as f:
            json.dump(mappings, f, indent=2)
        print(f"✅ Mappings created: {mappings_file}")
        
        # Also create mappings where cache manager expects them
        cache_manager_mappings_dir = python_server_dir / "ai_services" / "metadata" / "__cache"
        cache_manager_mappings_dir.mkdir(parents=True, exist_ok=True)
        cache_manager_mappings_file = cache_manager_mappings_dir / "files_mappings.json"
        
        with open(cache_manager_mappings_file, 'w', encoding='utf-8') as f:
            json.dump(mappings, f, indent=2)
        print(f"✅ Also created mappings for cache manager: {cache_manager_mappings_file}")
        
        # Step 3: Extract initial metadata and create cache
        print("\n3️⃣ Extracting metadata and creating cache...")
        extractor = PowerPointMetadataExtractor()
        metadata = extractor.extract_presentation_metadata(test_file)
        
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
        
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, indent=2, ensure_ascii=False)
        print(f"✅ Cache created with {len(metadata['slides'])} slides")
        
        # Also create cache where cache manager ACTUALLY expects it (ai_services/metadata/_cache/)
        cache_manager_cache_dir = python_server_dir / "ai_services" / "metadata" / "_cache"
        cache_manager_cache_dir.mkdir(parents=True, exist_ok=True)
        cache_manager_cache_file = cache_manager_cache_dir / "powerpoint_metadata_hotcache.json"
        
        with open(cache_manager_cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, indent=2, ensure_ascii=False)
        print(f"✅ Also created cache for cache manager: {cache_manager_cache_file}")
        
        # Step 4: Add objects using PowerPoint writer
        print("\n4️⃣ Adding objects using PowerPoint writer...")
        writer = PowerPointWriter()
        
        slide_data = {
            "1": {
                "Test Title": {
                    "type": "textbox",
                    "left": 100,
                    "top": 50,
                    "width": 400,
                    "height": 80,
                    "text": "Cache Test Title"
                },
                "Test Content": {
                    "type": "textbox", 
                    "left": 100,
                    "top": 150,
                    "width": 400,
                    "height": 100,
                    "text": "This tests cache updating"
                }
            },
            "2": {
                "Slide 2 Title": {
                    "type": "textbox",
                    "left": 100,
                    "top": 50,
                    "width": 400,  
                    "height": 80,
                    "text": "Second Slide"
                }
            }
        }
        
        success, updated_shapes = writer.write_to_existing(slide_data, test_file)
        print(f"✅ PowerPoint writer: Success={success}, {len(updated_shapes)} shapes updated")
        
        if updated_shapes:
            print("Updated shapes:")
            for shape in updated_shapes:
                print(f"  - {shape.get('shape_name', 'Unknown')} on slide {shape.get('slide_number')}")
        
        # Step 5: Update cache using cache manager
        print("\n5️⃣ Updating cache using cache manager...")
        cache_success = update_powerpoint_cache(workspace_path, updated_shapes)
        print(f"Cache update result: {cache_success}")
        
        # Step 6: READ AND VERIFY THE UPDATED CACHE (from the file that cache manager actually updated)
        print("\n6️⃣ VERIFYING UPDATED CACHE CONTENT...")
        
        # Read from the cache file that the cache manager actually updated
        cache_manager_cache_file = python_server_dir / "ai_services" / "metadata" / "_cache" / "powerpoint_metadata_hotcache.json"
        
        if cache_manager_cache_file.exists():
            with open(cache_manager_cache_file, 'r', encoding='utf-8') as f:
                final_cache_data = json.load(f)
            print(f"✅ Reading from cache manager's cache file: {cache_manager_cache_file}")
            
            print("✅ Successfully read updated cache file")
            
            if cache_key in final_cache_data:
                presentation = final_cache_data[cache_key]
                slides = presentation.get("slides", [])
                
                print(f"📊 Cache contains {len(slides)} slides")
                
                for slide in slides:
                    slide_num = slide.get("slideNumber")
                    shapes = slide.get("shapes", [])
                    print(f"  📄 Slide {slide_num}: {len(shapes)} shapes")
                    
                    for shape in shapes:
                        name = shape.get("name", "Unknown")
                        last_modified = shape.get("lastModified", "Never")
                        editing_history = shape.get("editingHistory", [])
                        print(f"    🔷 Shape: {name}")
                        print(f"       Last modified: {last_modified}")
                        print(f"       Edit history: {len(editing_history)} entries")
                
                # Verify expected shapes exist
                expected_shapes = ["Test Title", "Test Content", "Slide 2 Title"]
                found_shapes = []
                
                for slide in slides:
                    for shape in slide.get("shapes", []):
                        shape_name = shape.get("name")
                        if shape_name in expected_shapes:
                            found_shapes.append(shape_name)
                
                print(f"\n🔍 VERIFICATION RESULTS:")
                print(f"   Expected shapes: {expected_shapes}")
                print(f"   Found shapes: {found_shapes}")
                
                if len(found_shapes) == len(expected_shapes):
                    print("✅ SUCCESS: All expected shapes found in cache!")
                    print("✅ Cache update works correctly!")
                elif len(found_shapes) > 0:
                    missing = [s for s in expected_shapes if s not in found_shapes]
                    print(f"⚠️  PARTIAL: Found {len(found_shapes)}/{len(expected_shapes)} shapes")
                    print(f"   Missing: {missing}")
                else:
                    print("❌ FAILED: No expected shapes found in cache")
                    
            else:
                print(f"❌ Cache key '{cache_key}' not found in cache")
                print(f"Available keys: {list(final_cache_data.keys())}")
        else:
            print("❌ Cache file does not exist after update")
        
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        # Clean up only the PowerPoint file, leave cache files for manual verification
        cleanup_files = [test_file]
        print(f"\n🧹 Cleaning up PowerPoint file only (leaving cache for manual verification)...")
        for file_path in cleanup_files:
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    print(f"   Removed: {file_path}")
                except:
                    print(f"   Could not remove: {file_path}")
        
        # Print cache file location for manual verification
        cache_manager_cache_file = python_server_dir / "ai_services" / "metadata" / "_cache" / "powerpoint_metadata_hotcache.json"
        print(f"\n📁 Cache file location for manual verification: {cache_manager_cache_file}")

if __name__ == "__main__":
    test_cache_verification()
