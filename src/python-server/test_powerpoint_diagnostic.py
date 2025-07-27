import win32com.client as win32
import os
import tempfile

def points_to_emu(points):
    """Convert points to EMUs (English Metric Units)"""
    return int(points * 12700)

def test_different_approaches():
    """Test different approaches to create shapes"""
    
    temp_dir = tempfile.gettempdir()
    test_file = os.path.join(temp_dir, "powerpoint_diagnostic_test.pptx")
    
    try:
        # Initialize PowerPoint
        print("Initializing PowerPoint...")
        ppt = win32.Dispatch("PowerPoint.Application")
        ppt.Visible = True
        
        # Create new presentation
        presentation = ppt.Presentations.Add()
        
        # Try different slide layouts
        print("Available slide layouts:")
        for i, layout in enumerate(presentation.SlideMaster.CustomLayouts):
            try:
                print(f"  Layout {i}: {layout.Name}")
            except:
                print(f"  Layout {i}: <unnamed>")
        
        # Add a slide with title and content layout (index 1)
        try:
            slide_layout = presentation.SlideMaster.CustomLayouts[1]  # Title and Content
            slide = presentation.Slides.AddSlide(1, slide_layout)
            print("✅ Successfully created slide with Title and Content layout")
        except Exception as e:
            print(f"❌ Failed with Title and Content layout: {e}")
            # Fallback to blank layout
            slide_layout = presentation.SlideMaster.CustomLayouts[6]  # Blank
            slide = presentation.Slides.AddSlide(1, slide_layout)
            print("✅ Successfully created slide with Blank layout")
        
        # Test different shape creation methods
        print("\n=== Testing Different Shape Creation Methods ===")
        
        # Method 1: Using msoShapeRectangle constant (1)
        print("Method 1: Using shape constant 1 (msoShapeRectangle)")
        try:
            left_emu = points_to_emu(100)
            top_emu = points_to_emu(100)
            width_emu = points_to_emu(144)  # 2 inches
            height_emu = points_to_emu(72)   # 1 inch
            
            shape1 = slide.Shapes.AddShape(1, left_emu, top_emu, width_emu, height_emu)
            shape1.Name = "Method1_Rectangle" 
            print("✅ Method 1: SUCCESS")
            
        except Exception as e:
            print(f"❌ Method 1: FAILED - {e}")
        
        # Method 2: Using different shape constant
        print("Method 2: Using shape constant 5 (msoShapeOval)")
        try:
            left_emu = points_to_emu(300)
            top_emu = points_to_emu(100) 
            width_emu = points_to_emu(144)
            height_emu = points_to_emu(72)
            
            shape2 = slide.Shapes.AddShape(5, left_emu, top_emu, width_emu, height_emu)  # Oval
            shape2.Name = "Method2_Oval"
            print("✅ Method 2: SUCCESS")
            
        except Exception as e:
            print(f"❌ Method 2: FAILED - {e}")
        
        # Method 3: Try using AddTextbox instead
        print("Method 3: Using AddTextbox")
        try:
            left_emu = points_to_emu(100)
            top_emu = points_to_emu(200)
            width_emu = points_to_emu(144)
            height_emu = points_to_emu(72)
            
            shape3 = slide.Shapes.AddTextbox(1, left_emu, top_emu, width_emu, height_emu)  # msoTextOrientationHorizontal = 1
            shape3.Name = "Method3_Textbox"
            print("✅ Method 3: SUCCESS")
            
        except Exception as e:
            print(f"❌ Method 3: FAILED - {e}")
            
        # Method 4: Try without EMU conversion (direct points - this will likely fail)
        print("Method 4: Using direct points (no EMU conversion)")
        try:
            shape4 = slide.Shapes.AddShape(1, 100, 300, 144, 72)  # Direct points
            shape4.Name = "Method4_DirectPoints"
            print("✅ Method 4: SUCCESS")
            
        except Exception as e:
            print(f"❌ Method 4: FAILED - {e}")
            
        # Method 5: Try with floating point EMUs
        print("Method 5: Using floating point EMUs")
        try:
            left_emu = 100.0 * 12700
            top_emu = 350.0 * 12700
            width_emu = 144.0 * 12700
            height_emu = 72.0 * 12700
            
            shape5 = slide.Shapes.AddShape(1, left_emu, top_emu, width_emu, height_emu)
            shape5.Name = "Method5_FloatEMU"
            print("✅ Method 5: SUCCESS")
            
        except Exception as e:
            print(f"❌ Method 5: FAILED - {e}")
        
        # Check slide dimensions
        print(f"\n=== Slide Information ===")
        try:
            print(f"Slide width: {presentation.PageSetup.SlideWidth / 12700:.1f} points")
            print(f"Slide height: {presentation.PageSetup.SlideHeight / 12700:.1f} points")
        except Exception as e:
            print(f"Could not get slide dimensions: {e}")
        
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
    print("PowerPoint Shape Creation Diagnostic Test")
    print("="*50)
    test_different_approaches()
