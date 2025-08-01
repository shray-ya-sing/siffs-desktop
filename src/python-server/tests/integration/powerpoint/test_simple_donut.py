import win32com.client as win32
import pythoncom
import os

def create_simple_donut_chart():
    """Create a simple doughnut chart directly using COM."""
    
    # Initialize COM
    pythoncom.CoInitialize()
    
    try:
        # Create PowerPoint application
        ppt_app = win32.Dispatch("PowerPoint.Application")
        ppt_app.Visible = True
        
        # Create a new presentation
        presentation = ppt_app.Presentations.Add()
        
        # Add a slide with Title and Content layout
        slide_layout = presentation.SlideMaster.CustomLayouts(2)
        slide = presentation.Slides.AddSlide(1, slide_layout)
        
        print("=== Creating Doughnut Chart ===")
        
        # Use the correct doughnut chart constant: xlDoughnut = -4120
        chart_type = -4120
        
        # Position and size for the chart
        left, top, width, height = 100, 100, 300, 200
        
        try:
            # Create the chart
            chart_shape = slide.Shapes.AddChart(chart_type, left, top, width, height)
            chart = chart_shape.Chart
            
            print(f"Chart created - Requested: {chart_type}, Actual: {chart.ChartType}")
            
            # Set chart title
            chart.HasTitle = True
            chart.ChartTitle.Text = "Sample Doughnut Chart"
            
            # Get the chart data workbook
            workbook = chart.ChartData.Workbook
            worksheet = workbook.Worksheets(1)
            
            # Clear existing data
            worksheet.UsedRange.Clear()
            
            # Add our custom data
            print("Adding chart data...")
            worksheet.Cells(1, 1).Value = "Category"
            worksheet.Cells(1, 2).Value = "Value"
            worksheet.Cells(2, 1).Value = "Apple"
            worksheet.Cells(2, 2).Value = 40
            worksheet.Cells(3, 1).Value = "Orange"
            worksheet.Cells(3, 2).Value = 30
            worksheet.Cells(4, 1).Value = "Banana"
            worksheet.Cells(4, 2).Value = 30
            
            # DON'T close the workbook - this was the key issue!
            # workbook.Close()  # <-- This line was causing problems
            
            # Verify the chart type is still correct
            final_type = chart.ChartType
            print(f"Final chart type: {final_type}")
            
            if final_type == chart_type:
                print("✓ SUCCESS: Doughnut chart created and type persisted!")
            else:
                print(f"✗ WARNING: Chart type changed from {chart_type} to {final_type}")
                # Try to set it back
                chart.ChartType = chart_type
                print(f"Reset chart type to: {chart.ChartType}")
            
            # Save the presentation
            output_path = os.path.join(os.getcwd(), "simple_donut_test.pptx")
            presentation.SaveAs(output_path)
            print(f"Saved presentation to: {output_path}")
            
            print("\n=== Chart Creation Complete ===")
            print("Check the PowerPoint file to see if the doughnut chart was created correctly!")
            
            input("Press Enter to close...")
            
        except Exception as e:
            print(f"Error creating chart: {e}")
            import traceback
            traceback.print_exc()
        
        # Clean up
        presentation.Close()
        ppt_app.Quit()
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        pythoncom.CoUninitialize()

if __name__ == "__main__":
    create_simple_donut_chart()
