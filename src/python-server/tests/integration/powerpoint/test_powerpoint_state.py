import win32com.client
import pythoncom
import time
from pathlib import Path


def check_existing_powerpoint_instances():
    """Check if PowerPoint is already running."""
    try:
        # Try to connect to existing PowerPoint instance
        app = win32com.client.GetActiveObject("PowerPoint.Application")
        print(f"Found existing PowerPoint instance with {app.Presentations.Count} presentations open")
        
        for i in range(1, app.Presentations.Count + 1):
            presentation = app.Presentations(i)
            print(f"  Presentation {i}: {presentation.Name} ({presentation.Slides.Count} slides)")
        
        return app
    except Exception as e:
        print(f"No existing PowerPoint instance found: {e}")
        return None


def test_powerpoint_application_state():
    """Test PowerPoint application state and duplication behavior."""
    print("=" * 70)
    print("POWERPOINT APPLICATION STATE ANALYSIS")
    print("=" * 70)
    
    test_file = r"C:\Users\shrey\projects\cori-apps\cori_app\src\python-server\powerpoint\editing\test_duplication.pptx"
    
    print("1. Checking for existing PowerPoint instances...")
    existing_app = check_existing_powerpoint_instances()
    
    print("\n2. Creating new PowerPoint application...")
    try:
        # Create new PowerPoint application (like PowerPointWorker does)
        new_app = win32com.client.Dispatch("PowerPoint.Application")
        new_app.Visible = True
        print("New PowerPoint application created successfully")
        
        print("\n3. Opening presentation...")
        presentation = new_app.Presentations.Open(test_file)
        print(f"Presentation opened: {presentation.Name} with {presentation.Slides.Count} slides")
        
        print("\n4. Testing slide duplication...")
        start_time = time.time()
        
        try:
            source_slide = presentation.Slides(5)
            print(f"Got source slide 5")
            
            print("Calling Duplicate() method...")
            duplicated_slide = source_slide.Duplicate()
            print("Duplicate() completed")
            
            target_position = presentation.Slides.Count
            print(f"Moving to position {target_position}")
            duplicated_slide.MoveTo(target_position)
            print("MoveTo() completed")
            
            elapsed_time = time.time() - start_time
            print(f"✅ Duplication successful in {elapsed_time:.2f} seconds")
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            print(f"❌ Duplication failed after {elapsed_time:.2f} seconds: {e}")
        
        print("\n5. Checking final state...")
        print(f"Final slide count: {presentation.Slides.Count}")
        
        # Save and close
        presentation.Save()
        presentation.Close()
        new_app.Quit()
        
    except Exception as e:
        print(f"Error in test: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n6. Checking for remaining PowerPoint instances...")
    remaining_app = check_existing_powerpoint_instances()


def test_with_com_threading():
    """Test with COM threading like PowerPointWorker."""
    print("\n" + "=" * 70)
    print("TESTING WITH COM THREADING (like PowerPointWorker)")
    print("=" * 70)
    
    test_file = r"C:\Users\shrey\projects\cori-apps\cori_app\src\python-server\powerpoint\editing\test_duplication.pptx"
    
    # Initialize COM like PowerPointWorker does
    pythoncom.CoInitialize()
    print("COM initialized")
    
    try:
        print("Creating PowerPoint application...")
        app = win32com.client.Dispatch("PowerPoint.Application")
        app.Visible = True
        
        print("Opening presentation...")
        presentation = app.Presentations.Open(test_file)
        
        print("Testing duplication with COM threading...")
        start_time = time.time()
        
        source_slide = presentation.Slides(5)
        duplicated_slide = source_slide.Duplicate()
        duplicated_slide.MoveTo(presentation.Slides.Count)
        
        elapsed_time = time.time() - start_time
        print(f"✅ COM threading duplication successful in {elapsed_time:.2f} seconds")
        
        presentation.Save()
        presentation.Close()
        app.Quit()
        
    except Exception as e:
        elapsed_time = time.time() - start_time
        print(f"❌ COM threading duplication failed after {elapsed_time:.2f} seconds: {e}")
        import traceback
        traceback.print_exc()
    finally:
        pythoncom.CoUninitialize()
        print("COM uninitialized")


if __name__ == "__main__":
    test_powerpoint_application_state()
    test_with_com_threading()
