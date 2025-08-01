import win32com.client as win32
import pythoncom
import os

def create_donut_with_proper_range():
    """Create a doughnut chart with properly set data range."""
    
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
        
        print("=== Creating Doughnut Chart with Proper Data Range ===")
        
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
            
            # Clear ALL existing data first
            print("Clearing existing data...")
            worksheet.UsedRange.Clear()
            
            # Add our custom data in a clean way
            print("Adding chart data...")
            worksheet.Cells(1, 1).Value = "Category"
            worksheet.Cells(1, 2).Value = "Value"
            worksheet.Cells(2, 1).Value = "Apple"
            worksheet.Cells(2, 2).Value = 40
            worksheet.Cells(3, 1).Value = "Orange"
            worksheet.Cells(3, 2).Value = 30
            worksheet.Cells(4, 1).Value = "Banana"
            worksheet.Cells(4, 2).Value = 30
            
            # Now set the data range explicitly to match our data
            print("Setting chart data range...")
            data_range = "A1:B4"  # This matches our data: headers + 3 data rows
            
            try:
                # Method 1: Try SetSourceData
                chart.SetSourceData(worksheet.Range(data_range))
                print(f"✓ SetSourceData successful with range: {data_range}")
            except Exception as e:
                print(f"SetSourceData failed: {e}")
                
                # Method 2: Try to set the data range through SeriesCollection
                try:
                    print("Trying SeriesCollection approach...")
                    # Clear existing series
                    while chart.SeriesCollection().Count > 0:
                        chart.SeriesCollection(1).Delete()
                    
                    # Add our series
                    series = chart.SeriesCollection().NewSeries()
                    series.Name = "Values"
                    series.Values = worksheet.Range("B2:B4")  # Our values
                    series.XValues = worksheet.Range("A2:A4")  # Our categories
                    
                    print("✓ SeriesCollection method successful")
                    
                except Exception as e2:
                    print(f"SeriesCollection method also failed: {e2}")
                    
                    # Method 3: Try ChartData.Activate and refresh
                    try:
                        print("Trying Activate and refresh...")
                        chart.ChartData.Activate()
                        chart.Refresh()
                        print("✓ Activate and refresh successful")
                    except Exception as e3:
                        print(f"Activate method also failed: {e3}")
            
            # Force chart type again to make sure it stays
            chart.ChartType = chart_type
            
            # Verify the chart type is still correct
            final_type = chart.ChartType
            print(f"Final chart type: {final_type}")
            
            if final_type == chart_type:
                print("✓ SUCCESS: Doughnut chart created and type persisted!")
            else:
                print(f"✗ WARNING: Chart type changed from {chart_type} to {final_type}")
            
            # Print some debug info about the data
            print(f"\n=== Chart Data Debug Info ===")
            print(f"SeriesCollection Count: {chart.SeriesCollection().Count}")
            for i in range(1, chart.SeriesCollection().Count + 1):
                series = chart.SeriesCollection(i)
                print(f"Series {i}: Name='{series.Name}'")
            
            # Save the presentation
            output_path = os.path.join(os.getcwd(), "donut_with_range_test.pptx")
            presentation.SaveAs(output_path)
            print(f"Saved presentation to: {output_path}")
            
            print("\n=== Chart Creation Complete ===")
            print("Check the PowerPoint file to see if the doughnut chart data is now correct!")
            
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
    create_donut_with_proper_range()
