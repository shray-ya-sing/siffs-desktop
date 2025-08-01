import win32com.client
import time
import os


def create_test_presentation():
    """Create a test PowerPoint presentation with 5 slides."""
    test_file = r"C:\Users\shrey\projects\cori-apps\cori_app\src\python-server\powerpoint\editing\test_duplication_simple.pptx"
    
    try:
        app = win32com.client.Dispatch("PowerPoint.Application")
        app.Visible = True
        presentation = app.Presentations.Add()

        # Add 5 slides with simple content
        slide_layout = presentation.SlideMaster.CustomLayouts(1)
        for i in range(1, 6):
            slide = presentation.Slides.AddSlide(i, slide_layout)
            # Add a simple text box to each slide
            text_box = slide.Shapes.AddTextbox(1, 100, 100, 300, 100)
            text_box.TextFrame.TextRange.Text = f"This is Slide {i}"
            text_box.Name = f"TextBox_{i}"

        # Save the presentation
        presentation.SaveAs(test_file)
        print(f"Created test presentation: {test_file}")
        
        presentation.Close()
        app.Quit()
        return test_file
        
    except Exception as e:
        print(f"Error creating test presentation: {e}")
        return None


def test_approach_1_builtin_duplicate(presentation, source_slide_number):
    """Test Approach 1: Using PowerPoint's built-in Duplicate method."""
    print("\n--- Testing Approach 1: Built-in Duplicate Method ---")
    try:
        start_time = time.time()
        
        source_slide = presentation.Slides(source_slide_number)
        print(f"Source slide found: Slide {source_slide_number}")
        
        # Use built-in duplicate method
        duplicated_slide = source_slide.Duplicate()
        print(f"Slide duplicated, moving to end...")
        
        # Move to the end
        duplicated_slide.MoveTo(presentation.Slides.Count)
        
        elapsed_time = time.time() - start_time
        print(f"✅ Approach 1 SUCCESS: Duplicated in {elapsed_time:.2f} seconds")
        return True
        
    except Exception as e:
        elapsed_time = time.time() - start_time
        print(f"❌ Approach 1 FAILED: {e} (after {elapsed_time:.2f} seconds)")
        return False


def test_approach_2_manual_copy(presentation, source_slide_number):
    """Test Approach 2: Manual copy using AddSlide and shape copying."""
    print("\n--- Testing Approach 2: Manual Copy Method ---")
    try:
        start_time = time.time()
        
        source_slide = presentation.Slides(source_slide_number)
        source_layout = source_slide.CustomLayout
        print(f"Source slide found: Slide {source_slide_number}")
        
        # Create new slide with same layout
        target_position = presentation.Slides.Count + 1
        new_slide = presentation.Slides.AddSlide(target_position, source_layout)
        print(f"New blank slide created at position {target_position}")
        
        # Copy all shapes from source to new slide
        shapes_copied = 0
        for shape in source_slide.Shapes:
            try:
                # Copy the shape
                shape.Copy()
                # Paste it to the new slide
                pasted_shapes = new_slide.Shapes.Paste()
                if pasted_shapes.Count > 0:
                    pasted_shape = pasted_shapes[0]
                    original_name = getattr(shape, 'Name', f'Shape_{shapes_copied + 1}')
                    pasted_shape.Name = f"{original_name}_copy"
                shapes_copied += 1
            except Exception as shape_error:
                print(f"Warning: Failed to copy shape '{getattr(shape, 'Name', 'Unknown')}': {shape_error}")
                continue
        
        elapsed_time = time.time() - start_time
        print(f"✅ Approach 2 SUCCESS: Copied {shapes_copied} shapes in {elapsed_time:.2f} seconds")
        return True
        
    except Exception as e:
        elapsed_time = time.time() - start_time
        print(f"❌ Approach 2 FAILED: {e} (after {elapsed_time:.2f} seconds)")
        return False


def test_approach_3_select_copy_paste(presentation, source_slide_number):
    """Test Approach 3: Select all shapes and copy/paste."""
    print("\n--- Testing Approach 3: Select All and Copy/Paste Method ---")
    try:
        start_time = time.time()
        
        source_slide = presentation.Slides(source_slide_number)
        source_layout = source_slide.CustomLayout
        print(f"Source slide found: Slide {source_slide_number}")
        
        # Create new slide with same layout
        target_position = presentation.Slides.Count + 1
        new_slide = presentation.Slides.AddSlide(target_position, source_layout)
        print(f"New blank slide created at position {target_position}")
        
        # Select all shapes on source slide
        if source_slide.Shapes.Count > 0:
            source_slide.Shapes.SelectAll()
            # Copy all selected shapes
            source_slide.Shapes.Range().Copy()
            # Paste to new slide
            new_slide.Shapes.Paste()
            print(f"Copied all {source_slide.Shapes.Count} shapes using SelectAll method")
        else:
            print("No shapes to copy on source slide")
        
        elapsed_time = time.time() - start_time
        print(f"✅ Approach 3 SUCCESS: Duplicated in {elapsed_time:.2f} seconds")
        return True
        
    except Exception as e:
        elapsed_time = time.time() - start_time
        print(f"❌ Approach 3 FAILED: {e} (after {elapsed_time:.2f} seconds)")
        return False


def main():
    """Main test function."""
    print("=" * 70)
    print("POWERPOINT SLIDE DUPLICATION APPROACH TESTING")
    print("=" * 70)
    
    # Create or use existing test file
    test_file = r"C:\Users\shrey\projects\cori-apps\cori_app\src\python-server\powerpoint\editing\test_duplication.pptx"
    
    if not os.path.exists(test_file):
        print("Test file not found, creating new one...")
        test_file = create_test_presentation()
        if not test_file:
            print("Failed to create test presentation. Exiting.")
            return
    else:
        print(f"Using existing test file: {test_file}")
    
    try:
        # Open PowerPoint and the presentation
        app = win32com.client.Dispatch("PowerPoint.Application")
        app.Visible = True
        presentation = app.Presentations.Open(test_file)
        
        original_slide_count = presentation.Slides.Count
        print(f"Presentation opened. Original slide count: {original_slide_count}")
        
        source_slide_number = 5
        if source_slide_number > original_slide_count:
            source_slide_number = original_slide_count
            
        print(f"Testing duplication of slide {source_slide_number}")
        
        # Test all approaches
        results = {}
        
        results['approach_1'] = test_approach_1_builtin_duplicate(presentation, source_slide_number)
        results['approach_2'] = test_approach_2_manual_copy(presentation, source_slide_number)
        results['approach_3'] = test_approach_3_select_copy_paste(presentation, source_slide_number)
        
        # Summary
        print("\n" + "=" * 70)
        print("TEST RESULTS SUMMARY")
        print("=" * 70)
        
        final_slide_count = presentation.Slides.Count
        slides_added = final_slide_count - original_slide_count
        
        print(f"Original slides: {original_slide_count}")
        print(f"Final slides: {final_slide_count}")
        print(f"Slides added: {slides_added}")
        print()
        
        for approach, success in results.items():
            status = "✅ SUCCESS" if success else "❌ FAILED"
            print(f"{approach.replace('_', ' ').title()}: {status}")
        
        print("\nLeaving PowerPoint open for manual inspection...")
        print("Check the presentation to verify the duplicated slides.")
        print("Close PowerPoint manually when finished.")
        
        # Save but don't close - leave open for inspection
        presentation.Save()
        
    except Exception as e:
        print(f"Error during testing: {e}")


if __name__ == "__main__":
    main()
