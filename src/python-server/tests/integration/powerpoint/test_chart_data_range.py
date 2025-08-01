import win32com.client as win32
import pythoncom
import os

def inspect_and_fix_chart_data_range():
    """Inspect the chart's data range and fix it programmatically."""
    
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
        
        print("=== Creating Doughnut Chart and Inspecting Data Range ===")
        
        # Use the correct doughnut chart constant: xlDoughnut = -4120
        chart_type = -4120
        
        # Position and size for the chart
        left, top, width, height = 100, 100, 300, 200
        
        try:
            # Create the chart
            chart_shape = slide.Shapes.AddChart(chart_type, left, top, width, height)
            chart = chart_shape.Chart
            
            print(f"Chart created - Type: {chart.ChartType}")
            
            # Set chart title
            chart.HasTitle = True
            chart.ChartTitle.Text = "Data Range Test Chart"
            
            # Get the chart data workbook and worksheet
            workbook = chart.ChartData.Workbook
            worksheet = workbook.Worksheets(1)
            
            print("\n=== BEFORE: Inspecting Current Chart Data ===")
            
            # Method 1: Check current data range via SeriesCollection
            print(f"Current SeriesCollection Count: {chart.SeriesCollection().Count}")
            for i in range(1, chart.SeriesCollection().Count + 1):
                series = chart.SeriesCollection(i)
                print(f"Series {i}:")
                print(f"  Name: '{series.Name}'")
                try:
                    print(f"  Values: {series.Values}")
                    print(f"  XValues: {series.XValues}")
                except:
                    print("  Values/XValues: Could not access")
            
            # Method 2: Check the workbook's used range
            try:
                used_range = worksheet.UsedRange
                print(f"Current UsedRange: {used_range.Address}")
                print("Current data in UsedRange:")
                for row in range(1, used_range.Rows.Count + 1):
                    row_data = []
                    for col in range(1, used_range.Columns.Count + 1):
                        cell_value = worksheet.Cells(row, col).Value
                        row_data.append(str(cell_value) if cell_value is not None else "")
                    print(f"  Row {row}: {row_data}")
            except Exception as e:
                print(f"Could not read current UsedRange: {e}")
            
            # Method 3: Try to get the chart's data source directly
            try:
                # Some chart objects have a SourceData property
                if hasattr(chart, 'SourceData'):
                    print(f"Chart SourceData: {chart.SourceData}")
                else:
                    print("Chart does not have SourceData property")
            except Exception as e:
                print(f"Could not access SourceData: {e}")
            
            print("\n=== Clearing and Adding Our Data ===")
            
            # Clear ALL existing data
            worksheet.UsedRange.Clear()
            
            # Add our custom data
            data = [
                ["Category", "Value"],
                ["Apple", 40],
                ["Orange", 30], 
                ["Banana", 30]
            ]
            
            for row_idx, row_data in enumerate(data, 1):
                for col_idx, value in enumerate(row_data, 1):
                    worksheet.Cells(row_idx, col_idx).Value = value
            
            print("Added data:")
            for i, row in enumerate(data):
                print(f"  Row {i+1}: {row}")
            
            # Get the new used range
            new_used_range = worksheet.UsedRange
            print(f"New UsedRange after adding data: {new_used_range.Address}")
            
            print("\n=== Attempting Different Methods to Set Data Range ===")
            
            # Method 1: SetSourceData with the exact range we filled
            data_range_address = f"A1:B{len(data)}"
            print(f"Trying SetSourceData with range: {data_range_address}")
            try:
                chart.SetSourceData(worksheet.Range(data_range_address))
                print("✓ SetSourceData successful!")
            except Exception as e:
                print(f"✗ SetSourceData failed: {e}")
                
                # Method 2: Clear series and recreate manually
                print("Trying manual series recreation...")
                try:
                    # Remove all existing series
                    while chart.SeriesCollection().Count > 0:
                        chart.SeriesCollection(1).Delete()
                    
                    # Create new series
                    new_series = chart.SeriesCollection().NewSeries()
                    new_series.Name = "Values"
                    
                    # Set values and categories
                    values_range = f"B2:B{len(data)}"
                    categories_range = f"A2:A{len(data)}"
                    
                    new_series.Values = worksheet.Range(values_range)
                    new_series.XValues = worksheet.Range(categories_range)
                    
                    print(f"✓ Manual series creation successful!")
                    print(f"  Values range: {values_range}")
                    print(f"  Categories range: {categories_range}")
                    
                except Exception as e2:
                    print(f"✗ Manual series creation failed: {e2}")
                    
                    # Method 3: Try using ChartData.Activate() and Refresh()
                    print("Trying ChartData.Activate() approach...")
                    try:
                        chart.ChartData.Activate()
                        # The workbook should now be active, try to select our range
                        worksheet.Range(data_range_address).Select()
                        chart.Refresh()
                        print("✓ Activate and refresh successful!")
                        
                    except Exception as e3:
                        print(f"✗ Activate approach failed: {e3}")
            
            # Ensure chart type is still correct
            chart.ChartType = chart_type
            
            print("\n=== AFTER: Final Chart Data Inspection ===")
            print(f"Final SeriesCollection Count: {chart.SeriesCollection().Count}")
            for i in range(1, chart.SeriesCollection().Count + 1):
                series = chart.SeriesCollection(i)
                print(f"Series {i}:")
                print(f"  Name: '{series.Name}'")
                try:
                    values = series.Values
                    xvalues = series.XValues  
                    print(f"  Values: {values}")
                    print(f"  XValues: {xvalues}")
                except Exception as e:
                    print(f"  Could not read series data: {e}")
            
            # Save the presentation
            output_path = os.path.join(os.getcwd(), "chart_data_range_test.pptx")
            presentation.SaveAs(output_path)
            print(f"\nSaved presentation to: {output_path}")
            
            print("\n=== Test Complete ===")
            print("Check the PowerPoint file to see the result!")
            
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
    inspect_and_fix_chart_data_range()
