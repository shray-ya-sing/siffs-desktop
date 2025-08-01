import win32com.client
import time


def test_slide_duplication_manual(file_path: str):
    """Test slide duplication in PowerPoint using direct COM operations."""
    try:
        # Initialize PowerPoint application
        app = win32com.client.Dispatch("PowerPoint.Application")
        app.Visible = True

        # Open the presentation
        presentation = app.Presentations.Open(file_path)

        # Get the slide to be duplicated
        source_slide = presentation.Slides(5)

        # Start timing
        start_time = time.time()

        try:
            # Use the built-in Duplicate method
            duplicated_slide = source_slide.Duplicate()
            duplicated_slide.MoveTo(presentation.Slides.Count + 1)

            elapsed_time = time.time() - start_time
            print(f"Slide duplicated successfully in {elapsed_time:.2f} seconds using built-in method.")

        except Exception as e:
            print(f"Duplicate method failed: {e}")

        # Clean up
        presentation.Save()
        presentation.Close()
        app.Quit()

    except Exception as e:
        print(f"Error during slide duplication test: {e}")


if __name__ == "__main__":
    test_file_path = r"C:\\Users\\shrey\\projects\\cori-apps\\cori_app\\src\\python-server\\powerpoint\\editing\\test_duplication.pptx"
    test_slide_duplication_manual(test_file_path)

