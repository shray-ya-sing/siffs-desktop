import win32com.client as win32
import pythoncom
import os

def create_multiple_donut_charts():
    """Create multiple doughnut charts using the correct approach."""
    
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
        
        print("=== Creating Multiple Doughnut Charts ===")
        
        # Use the correct doughnut chart constant: xlDoughnut = -4120
        chart_type = -4120
        
        # Define different datasets for our charts
        chart_datasets = [
            {
                "title": "Q1 Sales",
                "data": [
                    ["Product", "Sales"],
                    ["Laptops", 45],
                    ["Phones", 35],
                    ["Tablets", 20]
                ],
                "position": (50, 50, 280, 180)  # left, top, width, height
            },
            {
                "title": "Q2 Sales", 
                "data": [
                    ["Product", "Sales"],
                    ["Laptops", 50],
                    ["Phones", 30],
                    ["Tablets", 20]
                ],
                "position": (350, 50, 280, 180)
            },
            {
                "title": "Market Share",
                "data": [
                    ["Company", "Share"],
                    ["Us", 40],
                    ["Competitor A", 35],
                    ["Competitor B", 25]
                ],
                "position": (50, 250, 280, 180)
            },
            {
                "title": "Regional Sales",
                "data": [
                    ["Region", "Revenue"],
                    ["North", 60],
                    ["South", 25],
                    ["East", 15]
                ],
                "position": (350, 250, 280, 180)
            }
        ]
        
        successful_charts = 0
        
        for i, chart_config in enumerate(chart_datasets, 1):
            print(f"\n=== Creating Chart {i}: {chart_config['title']} ===")
            
            try:
                # Get position and size
                left, top, width, height = chart_config["position"]
                
                # Create the chart
                chart_shape = slide.Shapes.AddChart(chart_type, left, top, width, height)
                chart = chart_shape.Chart
                
                print(f"Chart {i} created - Type: {chart.ChartType}")
                
                # Set chart title
                chart.HasTitle = True
                chart.ChartTitle.Text = chart_config["title"]
                
                # Get the chart data workbook and worksheet
                workbook = chart.ChartData.Workbook
                worksheet = workbook.Worksheets(1)
                
                # CRITICAL: Activate the chart data first  
                chart.ChartData.Activate()
                
                # Clear existing data in the worksheet
                worksheet.UsedRange.Clear()
                
                # Add our data to the worksheet
                chart_data = chart_config["data"]
                
                print(f"Adding data for {chart_config['title']}...")
                for row_idx, row_data in enumerate(chart_data, 1):
                    for col_idx, value in enumerate(row_data, 1):
                        worksheet.Cells(row_idx, col_idx).Value = value
                
                # Get the existing series and modify it directly
                series = chart.SeriesCollection(1)
                print(f"Modifying series for {chart_config['title']}...")
                
                # Extract values and categories from our data (skip header row)
                values = tuple(row[1] for row in chart_data[1:])  # Second column, skip header
                categories = tuple(row[0] for row in chart_data[1:])  # First column, skip header
                
                # Set values directly using tuples
                series.Name = chart_config["title"]
                series.Values = values
                series.XValues = categories
                
                print(f"✓ Chart {i} data set successfully:")
                print(f"  Values: {values}")
                print(f"  Categories: {categories}")
                
                # Ensure chart type is still correct
                chart.ChartType = chart_type
                
                # Verify the final result
                final_values = series.Values
                final_categories = series.XValues
                print(f"✓ Verified - Values: {final_values}")
                print(f"✓ Verified - Categories: {final_categories}")
                
                successful_charts += 1
                
            except Exception as e:
                print(f"✗ Error creating chart {i} ({chart_config['title']}): {e}")
                import traceback
                traceback.print_exc()
        
        print(f"\n=== Summary ===")
        print(f"Successfully created {successful_charts} out of {len(chart_datasets)} charts")
        
        # Save the presentation
        output_path = os.path.join(os.getcwd(), "multiple_donut_charts_test.pptx")
        presentation.SaveAs(output_path)
        print(f"Saved presentation to: {output_path}")
        
        print("\n=== Test Complete ===")
        print("Check the PowerPoint file to see all the doughnut charts!")
        
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
    create_multiple_donut_charts()
