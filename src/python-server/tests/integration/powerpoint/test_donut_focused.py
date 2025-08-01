import win32com.client as win32
import pythoncom
import os
import time

def test_donut_chart_focused():
    """Focused test to ensure doughnut chart type persists."""
    
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
        
        print("=== STEP 1: Created presentation and slide ===")
        
        # Chart creation parameters
        chart_type = 83  # msoChartTypeDoughnut
        left, top, width, height = 100, 100, 400, 300
        
        print(f"=== STEP 2: Creating chart with type {chart_type} (doughnut) ===")
        
        # Create the chart using AddChart (since AddChart2 failed)
        chart_shape = slide.Shapes.AddChart(chart_type, left, top, width, height)
        chart = chart_shape.Chart
        
        print(f"Chart type immediately after creation: {chart.ChartType}")
        
        # Force chart type to doughnut BEFORE doing anything else
        print("=== STEP 3: Forcing chart type to doughnut ===")
        chart.ChartType = 83  # Force doughnut
        print(f"Chart type after forcing to doughnut: {chart.ChartType}")
        
        # Small delay to let PowerPoint process the change
        time.sleep(0.5)
        
        # Check again
        print(f"Chart type after delay: {chart.ChartType}")
        
        # Now populate data
        print("=== STEP 4: Populating chart data ===")
        workbook = chart.ChartData.Workbook
        worksheet = workbook.Worksheets(1)
        
        # Clear existing data
        worksheet.UsedRange.Clear()
        
        # Set up data
        categories = ['Toronto', 'Calgary', 'Ottawa']
        values = [51, 39, 10]
        
        # Headers
        worksheet.Cells(1, 1).Value = "Category"
        worksheet.Cells(1, 2).Value = "Value"
        
        # Data
        for i, (category, value) in enumerate(zip(categories, values), start=2):
            worksheet.Cells(i, 1).Value = category
            worksheet.Cells(i, 2).Value = value
            print(f"Set: {category} = {value}")
        
        print(f"Chart type after populating data: {chart.ChartType}")
        
        # Force chart type again if it changed
        if chart.ChartType != 83:
            print(f"WARNING: Chart type changed to {chart.ChartType}! Forcing back to doughnut...")
            chart.ChartType = 83
            print(f"Chart type after re-forcing: {chart.ChartType}")
        
        # Try different doughnut chart types
        print("=== STEP 5: Trying different doughnut chart constants ===")
        
        # Try other doughnut-related constants
        doughnut_types = {
            "msoChartTypeDoughnut": 83,
            "xlDoughnut": -4120,
            "xlDoughnutExploded": 80
        }
        
        for name, chart_type_val in doughnut_types.items():
            try:
                print(f"Trying {name} (value {chart_type_val})...")
                chart.ChartType = chart_type_val
                time.sleep(0.2)  # Small delay
                actual_type = chart.ChartType
                print(f"Result: Chart type is now {actual_type}")
                
                if actual_type == chart_type_val:
                    print(f"SUCCESS: {name} worked!")
                    break
                else:
                    print(f"FAILED: Expected {chart_type_val}, got {actual_type}")
            except Exception as e:
                print(f"ERROR with {name}: {e}")
        
        # Set title and legend
        print("=== STEP 6: Setting chart properties ===")
        chart.HasTitle = True
        chart.ChartTitle.Text = "City Distribution - Doughnut Chart"
        chart.HasLegend = True
        
        print(f"Final chart type: {chart.ChartType}")
        
        # Save the presentation
        output_path = os.path.join(os.getcwd(), "test_donut_focused.pptx")
        presentation.SaveAs(output_path)
        print(f"Saved to: {output_path}")
        
        print("\n=== KEEPING WORKBOOK OPEN ===")
        print("Check the chart in PowerPoint now!")
        
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
    test_donut_chart_focused()
