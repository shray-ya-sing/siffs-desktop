import win32com.client as win32
import pythoncom
import os

def create_donut_correct_approach():
    """Create a doughnut chart using the correct approach for embedded charts."""
    
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
        
        print("=== Creating Doughnut Chart with Correct Approach ===")
        
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
            chart.ChartTitle.Text = "Correct Approach Chart"
            
            # Get the chart data workbook and worksheet
            workbook = chart.ChartData.Workbook
            worksheet = workbook.Worksheets(1)
            
            print("\\n=== Using Correct Approach ===")
            
            # CRITICAL: Activate the chart data first
            chart.ChartData.Activate()
            
            # Clear existing data in the worksheet
            worksheet.UsedRange.Clear()
            
            # Add our data to the worksheet
            our_data = [
                ["Category", "Value"],
                ["Apple", 40],
                ["Orange", 30], 
                ["Banana", 30]
            ]
            
            print("Adding data to worksheet...")
            for row_idx, row_data in enumerate(our_data, 1):
                for col_idx, value in enumerate(row_data, 1):
                    worksheet.Cells(row_idx, col_idx).Value = value
                    print(f"  Cell({row_idx},{col_idx}) = {value}")
            
            # DON'T modify SeriesCollection directly - instead work with the existing series
            print("\\nModifying existing series...")
            
            # Get the first (and typically only) series
            series = chart.SeriesCollection(1)
            print(f"Current series name: '{series.Name}'")
            
            # Method 1: Try setting values directly as tuples
            try:
                print("Trying direct value assignment...")
                series.Name = "Fruit Sales"
                series.Values = (40, 30, 30)  # Direct tuple assignment
                series.XValues = ("Apple", "Orange", "Banana")  # Direct tuple assignment
                print("✓ Direct value assignment successful!")
                
            except Exception as e:
                print(f"✗ Direct assignment failed: {e}")
                
                # Method 2: Try using the worksheet range but with proper activation
                try:
                    print("Trying range assignment with activated worksheet...")
                    
                    # Make sure the workbook is the active one
                    workbook.Activate()
                    worksheet.Activate()
                    
                    # Now try range assignment
                    values_range = worksheet.Range("B2:B4")
                    categories_range = worksheet.Range("A2:A4")
                    
                    series.Values = values_range
                    series.XValues = categories_range
                    print("✓ Range assignment with activation successful!")
                    
                except Exception as e2:
                    print(f"✗ Range assignment failed: {e2}")
                    
                    # Method 3: Try using Formula approach
                    try:
                        print("Trying formula approach...")
                        
                        # Set formulas that reference the worksheet
                        series.Formula = "=SERIES(\"Fruit Sales\",Sheet1!$A$2:$A$4,Sheet1!$B$2:$B$4,1)"
                        print("✓ Formula approach successful!")
                        
                    except Exception as e3:
                        print(f"✗ Formula approach failed: {e3}")
            
            # Ensure chart type is still correct
            chart.ChartType = chart_type
            print(f"Final chart type: {chart.ChartType}")
            
            # Final check of series data
            print("\\n=== Final Series Check ===")
            for i in range(1, chart.SeriesCollection().Count + 1):
                series = chart.SeriesCollection(i)
                print(f"Series {i}: Name='{series.Name}'")
                try:
                    values = series.Values
                    xvalues = series.XValues
                    print(f"  Values: {values}")
                    print(f"  XValues: {xvalues}")
                except Exception as e:
                    print(f"  Could not read series data: {e}")
            
            # IMPORTANT: Don't close the workbook!
            # workbook.Close()  # This would reset everything
            
            # Save the presentation
            output_path = os.path.join(os.getcwd(), "correct_approach_test.pptx")
            presentation.SaveAs(output_path)
            print(f"\\nSaved presentation to: {output_path}")
            
            print("\\n=== Test Complete ===")
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
    create_donut_correct_approach()
