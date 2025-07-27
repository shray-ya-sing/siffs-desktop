import win32com.client as win32
import os
import tempfile

def test_direct_points_limits():
    """Test PowerPoint limits using direct points (no EMU conversion)"""
    
    temp_dir = tempfile.gettempdir()
    test_file = os.path.join(temp_dir, "powerpoint_final_test.pptx")
    
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
        
        # Get actual slide dimensions
        slide_width = presentation.PageSetup.SlideWidth
        slide_height = presentation.PageSetup.SlideHeight
        print(f"Actual slide dimensions: {slide_width} x {slide_height} EMUs")
        print(f"Slide dimensions in points: {slide_width/12700:.1f} x {slide_height/12700:.1f}")
        
        # Test width limits with direct points
        print("\n=== Testing Width Limits (using direct points) ===")
        width_tests = [100, 200, 300, 400, 500, 600, 700, 720, 800, 900, 1000]
        
        results = {"max_width": 0, "max_height": 0}
        
        for width in width_tests:
            try:
                shape = slide.Shapes.AddShape(1, 50, 50, width, 100)  # Rectangle at (50,50) with height 100
                shape.Name = f"TestRect_W{width}"
                print(f"✅ Width {width} points: SUCCESS")
                results["max_width"] = width
                
            except Exception as e:
                print(f"❌ Width {width} points: FAILED - {str(e)}")
                break
        
        # Test height limits with direct points
        print("\n=== Testing Height Limits (using direct points) ===")
        height_tests = [50, 100, 150, 200, 250, 300, 350, 400, 450, 500, 540, 600]
        
        for height in height_tests:
            try:
                shape = slide.Shapes.AddShape(1, 200, 50, 200, height)  # Rectangle at (200,50) with width 200
                shape.Name = f"TestRect_H{height}"
                print(f"✅ Height {height} points: SUCCESS")
                results["max_height"] = height
                
            except Exception as e:
                print(f"❌ Height {height} points: FAILED - {str(e)}")
                break
        
        # Test position limits
        print("\n=== Testing Position Limits (using direct points) ===")
        left_tests = [0, 100, 200, 400, 600, 700, 720, 800, 900, 1000]
        
        for left in left_tests:
            try:
                shape = slide.Shapes.AddShape(1, left, 100, 100, 50)  # Small rectangle
                shape.Name = f"TestRect_L{left}"
                print(f"✅ Left {left} points: SUCCESS")
                
            except Exception as e:
                print(f"❌ Left {left} points: FAILED - {str(e)}")
                break
        
        top_tests = [0, 100, 200, 300, 400, 500, 540, 600, 700]
        
        for top in top_tests:
            try:
                shape = slide.Shapes.AddShape(1, 100, top, 100, 50)  # Small rectangle
                shape.Name = f"TestRect_T{top}"
                print(f"✅ Top {top} points: SUCCESS")
                
            except Exception as e:
                print(f"❌ Top {top} points: FAILED - {str(e)}")
                break
        
        # Summary
        print(f"\n" + "="*60)
        print("FINAL RESULTS")
        print("="*60)
        print(f"Maximum successful width: {results['max_width']} points")
        print(f"Maximum successful height: {results['max_height']} points")
        print(f"Slide dimensions: {slide_width/12700:.1f} x {slide_height/12700:.1f} points")
        
        # Save the test presentation
        presentation.SaveAs(test_file)
        print(f"\nTest presentation saved to: {test_file}")
        
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
    print("PowerPoint Direct Points Limits Test")
    print("="*50)
    results = test_direct_points_limits()
    
    if results:
        print(f"\nRecommended safe limits for your system:")
        print(f"- Maximum width: {results['max_width']} points")
        print(f"- Maximum height: {results['max_height']} points")
    else:
        print("Test failed!")
