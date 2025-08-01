import win32com.client as win32
import os
import tempfile

def points_to_emu(points):
    """Convert points to EMUs (English Metric Units)"""
    return int(points * 12700)

def test_shape_dimensions():
    """Test various width and height combinations to find PowerPoint limits"""
    
    # Create a temporary PowerPoint file
    temp_dir = tempfile.gettempdir()
    test_file = os.path.join(temp_dir, "powerpoint_dimension_test.pptx")
    
    try:
        # Initialize PowerPoint
        print("Initializing PowerPoint...")
        ppt = win32.Dispatch("PowerPoint.Application")
        ppt.Visible = True
        
        # Create new presentation
        presentation = ppt.Presentations.Add()
        
        # Add a slide with blank layout
        slide_layout = presentation.SlideMaster.CustomLayouts[6]  # Blank layout
        slide = presentation.Slides.AddSlide(1, slide_layout)
        
        print("Created new presentation with blank slide")
        
        # Test different width values (in points) - starting much smaller
        width_tests = [1, 5, 10, 20, 30, 50, 72, 100, 144, 200, 300, 400, 500, 600, 720]
        height_tests = [1, 5, 10, 20, 30, 50, 72, 100, 144, 200, 300, 400, 500, 540]
        
        results = {
            "width_limits": {"max_success": 0, "min_failure": None},
            "height_limits": {"max_success": 0, "min_failure": None},
            "test_results": []
        }
        
        print("\n=== Testing Width Limits (height fixed at 100 points) ===")
        
        # Test width limits with fixed height
        for width in width_tests:
            try:
                # Add rectangle shape at position (50, 50)
                left_emu = points_to_emu(50)
                top_emu = points_to_emu(50)
                width_emu = points_to_emu(width)
                height_emu = points_to_emu(100)  # Fixed height
                
                shape = slide.Shapes.AddShape(1, left_emu, top_emu, width_emu, height_emu)  # 1 = msoShapeRectangle
                shape.Name = f"TestRect_W{width}"
                
                print(f"✅ Width {width} points: SUCCESS")
                results["width_limits"]["max_success"] = max(results["width_limits"]["max_success"], width)
                results["test_results"].append({"test": "width", "value": width, "success": True, "error": None})
                
            except Exception as e:
                print(f"❌ Width {width} points: FAILED - {str(e)}")
                if results["width_limits"]["min_failure"] is None:
                    results["width_limits"]["min_failure"] = width
                results["test_results"].append({"test": "width", "value": width, "success": False, "error": str(e)})
        
        print(f"\n=== Testing Height Limits (width fixed at 200 points) ===")
        
        # Test height limits with fixed width
        for height in height_tests:
            try:
                # Add rectangle shape at position (100, 50)
                left_emu = points_to_emu(100)
                top_emu = points_to_emu(50)
                width_emu = points_to_emu(200)  # Fixed width
                height_emu = points_to_emu(height)
                
                shape = slide.Shapes.AddShape(1, left_emu, top_emu, width_emu, height_emu)  # 1 = msoShapeRectangle
                shape.Name = f"TestRect_H{height}"
                
                print(f"✅ Height {height} points: SUCCESS")
                results["height_limits"]["max_success"] = max(results["height_limits"]["max_success"], height)
                results["test_results"].append({"test": "height", "value": height, "success": True, "error": None})
                
            except Exception as e:
                print(f"❌ Height {height} points: FAILED - {str(e)}")
                if results["height_limits"]["min_failure"] is None:
                    results["height_limits"]["min_failure"] = height
                results["test_results"].append({"test": "height", "value": height, "success": False, "error": str(e)})
        
        # Save the test presentation
        presentation.SaveAs(test_file)
        print(f"\nTest presentation saved to: {test_file}")
        
        # Print summary
        print("\n" + "="*60)
        print("SUMMARY OF RESULTS")
        print("="*60)
        print(f"Maximum successful width: {results['width_limits']['max_success']} points")
        print(f"Minimum failed width: {results['width_limits']['min_failure']} points")
        print(f"Maximum successful height: {results['height_limits']['max_success']} points")
        print(f"Minimum failed height: {results['height_limits']['min_failure']} points")
        
        print(f"\nRecommended safe limits:")
        print(f"- Width: {results['width_limits']['max_success']} points or less")
        print(f"- Height: {results['height_limits']['max_success']} points or less")
        
        # Close presentation
        presentation.Close()
        ppt.Quit()
        
        return results
        
    except Exception as e:
        print(f"Error during testing: {e}")
        try:
            ppt.Quit()
        except:
            pass
        return None

if __name__ == "__main__":
    print("PowerPoint Shape Dimension Limits Test")
    print("="*50)
    results = test_shape_dimensions()
    
    if results:
        print("\nTest completed successfully!")
        
        # Detailed results
        print(f"\nDetailed Results:")
        for result in results["test_results"]:
            status = "✅" if result["success"] else "❌"
            print(f"{status} {result['test'].capitalize()} {result['value']}: {'SUCCESS' if result['success'] else 'FAILED'}")
            if not result["success"]:
                print(f"    Error: {result['error']}")
    else:
        print("Test failed!")
