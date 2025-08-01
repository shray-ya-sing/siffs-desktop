import json
from powerpoint.editing.powerpoint_writer import PowerPointWriter

# Mock JSON data for charts
mock_data = {
    "slide1": {
        "first_chart": {
            "chart_type": "doughnut",
            "chart_title": "Q1 Product Sales",
            "left": 100,
            "top": 100,
            "width": 300,
            "height": 200,
            "chart_data": {
                "categories": ["Laptops", "Phones", "Tablets"],
                "series": [
                    {
                        "name": "Sales",
                        "values": [45, 35, 20]
                    }
                ]
            }
        },
        "second_chart": {
            "chart_type": "doughnut",
            "chart_title": "Q2 Product Sales",
            "left": 450,
            "top": 100,
            "width": 300,
            "height": 200,
            "chart_data": {
                "categories": ["Laptops", "Phones", "Tablets"],
                "series": [
                    {
                        "name": "Sales",
                        "values": [50, 30, 20]
                    }
                ]
            }
        }
    }
}

# Test the creation of charts in PowerPoint
def test_create_charts_with_writer(output_filepath):
    writer = PowerPointWriter()
    success, updated_shapes = writer.write_to_existing(
        slide_data=mock_data,
        output_filepath=output_filepath
    )
    
    if success:
        print(f"Successfully created and updated charts. Updated shapes: {len(updated_shapes)}")
    else:
        print("Failed to create or update charts.")

if __name__ == "__main__":
    # Path to the output PowerPoint file
    output_file = "mock_charts_test.pptx"
    test_create_charts_with_writer(output_file)
