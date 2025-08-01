import win32com.client as win32
import os
import tempfile

def points_to_emu(points):
    """Convert points to EMUs (English Metric Units)"""
    return int(points * 12700)

def test_modify_shape_dimensions():
    """Test by creating a shape first, then modifying its dimensions"""
    
    # Create a temporary PowerPoint file  
    temp_dir = tempfile.gettempdir()
    test_file = os.path.join(temp_dir, "powerpoint_modify_test.pptx")
    
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
        
        # First, try to create a small rectangle that should work
        print("Creating initial small rectangle...")
        try:
            left_emu = points_to_emu(50)
            top_emu = points_to_emu(50) 
            width_emu = points_to_emu(72)  # 1 inch
            height_emu = points_to_emu(36)  # 0.5 inch
            
            shape = slide.Shapes.AddShape(1, left_emu, top_emu, width_emu, height_emu)
            shape.Name = "TestRect"
            print("✅ Successfully created initial rectangle (72x36 points)")
            
        except Exception as e:
            print(f"❌ Failed to create initial rectangle: {e}")
            
            # Try even smaller
            try:
                left_emu = points_to_emu(10)
                top_emu = points_to_emu(10)
                width_emu = points_to_emu(10) 
                height_emu = points_to_emu(10)
                
                shape = slide.Shapes.AddShape(1, left_emu, top_emu, width_emu, height_emu)
                shape.Name = "TestRect"
                print("✅ Successfully created tiny rectangle (10x10 points)")
                
            except Exception as e2:
                print(f"❌ Failed to create even tiny rectangle: {e2}")
                return None
        
        # Now test modifying width
        print("\n=== Testing Width Modification ===")
        width_tests = [20, 50, 72, 100, 144, 200, 300, 400, 500, 600, 720]
        
        for width in width_tests:
            try:
                shape.Width = points_to_emu(width)
                print(f"✅ Width {width} points: SUCCESS")
                
            except Exception as e:
                print(f"❌ Width {width} points: FAILED - {str(e)}")
                break  # Stop at first failure
        
        print("\n=== Testing Height Modification ===")
        height_tests = [20, 50, 72, 100, 144, 200, 300, 400, 500, 540]
        
        for height in height_tests:
            try:
                shape.Height = points_to_emu(height)
                print(f"✅ Height {height} points: SUCCESS")
                
            except Exception as e:
                print(f"❌ Height {height} points: FAILED - {str(e)}")
                break  # Stop at first failure
                
        # Test position modifications
        print("\n=== Testing Position Modification ===")
        left_tests = [0, 10, 50, 100, 200, 400, 600, 700, 720]
        
        for left in left_tests:
            try:
                shape.Left = points_to_emu(left)
                print(f"✅ Left {left} points: SUCCESS")
                
            except Exception as e:
                print(f"❌ Left {left} points: FAILED - {str(e)}")
                break
        
        top_tests = [0, 10, 50, 100, 200, 400, 500, 540]
        
        for top in top_tests:
            try:
                shape.Top = points_to_emu(top)
                print(f"✅ Top {top} points: SUCCESS")
                
            except Exception as e:
                print(f"❌ Top {top} points: FAILED - {str(e)}")
                break
        
        # Save the test presentation
        presentation.SaveAs(test_file)
        print(f"\nTest presentation saved to: {test_file}")
        
        # Close presentation
        presentation.Close()
        ppt.Quit()
        
        return True
        
    except Exception as e:
        print(f"Error during testing: {e}")
        try:
            ppt.Quit()
        except:
            pass
        return None

if __name__ == "__main__":
    print("PowerPoint Shape Modification Limits Test")
    print("="*50)
    test_modify_shape_dimensions()
