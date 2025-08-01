import win32com.client as win32
import pythoncom
import os
import time

def test_chart_types():
    """Test different chart type constants to find the correct doughnut chart."""
    
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
        
        print("=== Testing Different Chart Type Constants ===")
        
        # List of potential doughnut chart constants to test
        chart_types_to_test = [
            ("msoChartTypeDoughnut (manual)", 83),
            ("xlDoughnut (Excel constant)", -4120),
            ("xlDoughnutExploded", 80),
            ("Alternative 1", 18),  # Some sources suggest this
            ("Alternative 2", 19),  # Some sources suggest this
            ("Alternative 3", 84),  # Close to 83
            ("Alternative 4", 82),  # Close to 83
        ]
        
        for i, (name, chart_type) in enumerate(chart_types_to_test):
            print(f"\n=== Test {i+1}: {name} (value: {chart_type}) ===")
            
            try:
                # Create chart with this type
                left = 50 + (i % 3) * 200
                top = 50 + (i // 3) * 150
                width, height = 180, 120
                
                chart_shape = slide.Shapes.AddChart(chart_type, left, top, width, height)
                chart = chart_shape.Chart
                
                print(f"Created chart - Requested: {chart_type}, Actual: {chart.ChartType}")
                
                # Set a simple title to identify this chart
                chart.HasTitle = True
                chart.ChartTitle.Text = f"{name}\n(Type: {chart_type})"
                
                # Add simple data
                workbook = chart.ChartData.Workbook
                worksheet = workbook.Worksheets(1)
                worksheet.UsedRange.Clear()
                
                # Simple data
                worksheet.Cells(1, 1).Value = "A"
                worksheet.Cells(1, 2).Value = "B"
                worksheet.Cells(2, 1).Value = "Item1"
                worksheet.Cells(2, 2).Value = 30
                worksheet.Cells(3, 1).Value = "Item2"
                worksheet.Cells(3, 2).Value = 70
                
                # Check if chart type matches what we requested
                if chart.ChartType == chart_type:
                    print(f"✓ SUCCESS: Chart type {chart_type} accepted and matches!")
                else:
                    print(f"✗ MISMATCH: Requested {chart_type}, got {chart.ChartType}")
                
                # Force the chart type after data setup
                chart.ChartType = chart_type
                final_type = chart.ChartType
                
                print(f"After forcing type: {final_type}")
                
                if final_type == chart_type:
                    print(f"✓ Chart type {chart_type} persisted after data setup!")
                else:
                    print(f"✗ Chart type changed to {final_type} after data setup")
                
            except Exception as e:
                print(f"✗ ERROR creating chart with type {chart_type}: {e}")
        
        # Also try creating a chart and then checking what types are available
        print(f"\n=== Checking Available Chart Types ===")
        try:
            # Create a basic chart
            test_chart_shape = slide.Shapes.AddChart(5, 50, 400, 150, 100)  # Basic pie chart
            test_chart = test_chart_shape.Chart
            
            # Try some common chart types and see what we get
            common_types = [5, 51, 57, 65, 1, 83, -4120, 18, 19]
            
            for chart_type in common_types:
                try:
                    test_chart.ChartType = chart_type
                    actual = test_chart.ChartType
                    print(f"Set to {chart_type} -> Got {actual} ({'✓' if actual == chart_type else '✗'})")
                except Exception as e:
                    print(f"Cannot set chart type {chart_type}: {e}")
            
            # Clean up test chart
            test_chart_shape.Delete()
            
        except Exception as e:
            print(f"Error in chart type testing: {e}")
        
        # Save the presentation so we can visually inspect the charts
        output_path = os.path.join(os.getcwd(), "chart_types_test.pptx")
        presentation.SaveAs(output_path)
        print(f"\n=== Saved test charts to: {output_path} ===")
        print("Open this file to visually inspect which chart types created doughnut charts!")
        
        input("Press Enter to close...")
        
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
    test_chart_types()
