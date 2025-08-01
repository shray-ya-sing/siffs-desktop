import win32com.client as win32
import pythoncom
import os
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_donut_chart_direct():
    """Test doughnut chart creation with direct PowerPoint COM automation."""
    
    # Initialize COM
    pythoncom.CoInitialize()
    
    try:
        # Create PowerPoint application
        ppt_app = win32.Dispatch("PowerPoint.Application")
        ppt_app.Visible = True
        
        # Create a new presentation
        presentation = ppt_app.Presentations.Add()
        
        # Add a slide with Title and Content layout
        slide_layout = presentation.SlideMaster.CustomLayouts(2)  # Title and Content layout
        slide = presentation.Slides.AddSlide(1, slide_layout)
        
        print("=== STEP 1: Created presentation and slide ===")
        
        # Define chart data
        categories = ['Toronto', 'Calgary', 'Ottawa']
        values = [51, 39, 10]
        
        print(f"=== STEP 2: Chart data defined ===")
        print(f"Categories: {categories}")
        print(f"Values: {values}")
        
        # Create doughnut chart
        chart_type = 83  # msoChartTypeDoughnut
        left, top, width, height = 100, 100, 400, 300
        
        print(f"=== STEP 3: Creating doughnut chart (type {chart_type}) ===")
        
        # Create the chart shape - try AddChart2 first, fallback to AddChart
        try:
            chart_shape = slide.Shapes.AddChart2(chart_type, left, top, width, height)
            print("Successfully created chart using AddChart2")
        except Exception as e:
            print(f"AddChart2 failed: {e}")
            print("Trying AddChart fallback...")
            chart_shape = slide.Shapes.AddChart(chart_type, left, top, width, height)
            print("Successfully created chart using AddChart")
        
        chart = chart_shape.Chart
        
        print(f"Chart created with initial type: {chart.ChartType}")
        
        # Verify chart type immediately after creation
        if chart.ChartType != chart_type:
            print(f"WARNING: Chart type mismatch! Expected {chart_type}, got {chart.ChartType}")
            print("Correcting chart type...")
            chart.ChartType = chart_type
            print(f"Chart type after correction: {chart.ChartType}")
        
        print("=== STEP 4: Accessing chart data workbook ===")
        
        # Get the chart data workbook and worksheet
        workbook = chart.ChartData.Workbook
        worksheet = workbook.Worksheets(1)
        
        print(f"Workbook: {workbook}")
        print(f"Worksheet: {worksheet}")
        
        print("=== STEP 5: Populating chart data ===")
        
        # Clear existing data first
        used_range = worksheet.UsedRange
        if used_range:
            used_range.Clear()
            print("Cleared existing data")
        
        # Set up headers
        worksheet.Cells(1, 1).Value = "Category"
        worksheet.Cells(1, 2).Value = "Value"
        print("Set headers: Category, Value")
        
        # Populate categories and values
        for i, (category, value) in enumerate(zip(categories, values), start=2):
            worksheet.Cells(i, 1).Value = category
            worksheet.Cells(i, 2).Value = value
            print(f"Set row {i}: {category} = {value}")
        
        print("=== STEP 6: Verifying data in worksheet ===")
        
        # Verify the data was written correctly
        for i in range(1, len(categories) + 2):
            for j in range(1, 3):
                cell_value = worksheet.Cells(i, j).Value
                print(f"Cell ({i}, {j}): {cell_value}")
        
        print("=== STEP 7: Setting chart source data ===")
        
        # Set the chart data range
        data_range = f"A1:B{len(categories) + 1}"
        print(f"Setting chart source data to range: {data_range}")
        
        # Try multiple approaches for setting source data
        try:
            chart.SetSourceData(worksheet.Range(data_range))
            print("Chart source data set successfully using SetSourceData")
        except Exception as e1:
            print(f"SetSourceData failed: {e1}")
            try:
                # Try alternative approach with explicit range reference
                print("Trying alternative approach with range reference...")
                range_ref = worksheet.Range(data_range)
                chart.SetSourceData(range_ref, 2)  # 2 = xlColumns
                print("Chart source data set successfully using range reference")
            except Exception as e2:
                print(f"Range reference approach failed: {e2}")
                try:
                    # Try with ChartData.Activate() first
                    print("Trying with ChartData.Activate() first...")
                    chart.ChartData.Activate()
                    chart.SetSourceData(worksheet.Range(data_range))
                    print("Chart source data set successfully after Activate")
                except Exception as e3:
                    print(f"Activate approach failed: {e3}")
                    print("Skipping SetSourceData - chart may use existing data structure")
        
        # Verify chart type again after setting data
        print(f"Chart type after setting data: {chart.ChartType}")
        if chart.ChartType != chart_type:
            print(f"WARNING: Chart type changed after setting data! Expected {chart_type}, got {chart.ChartType}")
            print("Re-correcting chart type...")
            chart.ChartType = chart_type
            print(f"Chart type after re-correction: {chart.ChartType}")
        
        print("=== STEP 8: Setting chart properties ===")
        
        # Set chart title
        chart.HasTitle = True
        chart.ChartTitle.Text = "City Distribution"
        print("Set chart title")
        
        # Set legend
        chart.HasLegend = True
        print("Enabled legend")
        
        print("=== STEP 9: Final verification ===")
        
        # Final verification
        print(f"Final chart type: {chart.ChartType}")
        print(f"Chart title: {chart.ChartTitle.Text}")
        print(f"Has legend: {chart.HasLegend}")
        
        # Verify data one more time
        print("Final data verification:")
        for i in range(1, len(categories) + 2):
            for j in range(1, 3):
                cell_value = worksheet.Cells(i, j).Value
                print(f"Cell ({i}, {j}): {cell_value}")
        
        # Save the presentation
        output_path = os.path.join(os.getcwd(), "test_donut_direct.pptx")
        presentation.SaveAs(output_path)
        print(f"=== STEP 10: Presentation saved to {output_path} ===")
        
        print("\n=== DO NOT CLOSE WORKBOOK - KEEPING IT OPEN ===")
        print("Workbook will remain open to preserve chart data")
        
        input("Press Enter to close the presentation and exit...")
        
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
    test_donut_chart_direct()
