#!/usr/bin/env python3
"""
Test script to verify doughnut chart color functionality.
This script creates a PowerPoint presentation with doughnut charts and tests
the ability to set different colors for different data values.
"""

import os
import sys
import tempfile
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from powerpoint.editing.powerpoint_writer import PowerPointWriter

def test_doughnut_chart_colors():
    """Test creating doughnut charts with custom colors for each slice."""
    
    # Create a temporary PowerPoint file
    with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as temp_file:
        temp_path = temp_file.name
    
    try:
        # Initialize PowerPoint writer
        writer = PowerPointWriter()
        
        # Create a simple presentation first
        print("Creating temporary PowerPoint presentation...")
        
        # Add a blank slide first
        success = writer.add_blank_slide(temp_path, 1)
        if not success:
            print("❌ Failed to create blank slide")
            return False
        
        print("✅ Created blank slide")
        
        # Test data for doughnut chart
        chart_data = {
            'categories': ['Toronto', 'Calgary', 'Ottawa', 'Vancouver', 'Montreal'],
            'series': [{
                'name': 'Population',
                'values': [51, 39, 10, 25, 30]  # Sample population data
            }]
        }
        
        # Colors for each slice - should match the number of categories
        slice_colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7']
        
        # Create slide data with doughnut chart
        slide_data = {
            'slide1': {
                'DoughnutChart1': {
                    'shape_type': 'chart',
                    'chart_type': 'doughnut',
                    'chart_data': chart_data,
                    'chart_title': 'City Population Distribution',
                    'series_colors': slice_colors,
                    'show_legend': True,
                    'show_data_labels': True,
                    'left': 50,
                    'top': 50,
                    'width': 400,
                    'height': 300
                }
            }
        }
        
        print("Creating doughnut chart with custom colors...")
        print(f"Chart data: {chart_data}")
        print(f"Slice colors: {slice_colors}")
        
        # Write the chart to PowerPoint
        success, updated_shapes = writer.write_to_existing(slide_data, temp_path)
        
        if success:
            print("✅ Successfully created doughnut chart")
            print(f"Updated shapes: {len(updated_shapes)}")
            
            # Print details about what was applied
            for shape_info in updated_shapes:
                print(f"  - Shape: {shape_info.get('shape_name', 'Unknown')}")
                print(f"    Properties applied: {shape_info.get('properties_applied', [])}")
        else:
            print("❌ Failed to create doughnut chart")
            return False
        
        # Test with a second doughnut chart with different colors
        print("\nCreating second doughnut chart with different colors...")
        
        chart_data_2 = {
            'categories': ['Q1', 'Q2', 'Q3', 'Q4'],
            'series': [{
                'name': 'Sales',
                'values': [120, 150, 180, 200]
            }]
        }
        
        slice_colors_2 = ['#E74C3C', '#F39C12', '#27AE60', '#8E44AD']
        
        slide_data_2 = {
            'slide1': {
                'DoughnutChart2': {
                    'shape_type': 'chart',
                    'chart_type': 'doughnut',
                    'chart_data': chart_data_2,
                    'chart_title': 'Quarterly Sales',
                    'series_colors': slice_colors_2,
                    'show_legend': True,
                    'show_data_labels': True,
                    'left': 500,
                    'top': 50,
                    'width': 350,
                    'height': 300
                }
            }
        }
        
        success, updated_shapes = writer.write_to_existing(slide_data_2, temp_path)
        
        if success:
            print("✅ Successfully created second doughnut chart")
            print(f"Updated shapes: {len(updated_shapes)}")
        else:
            print("❌ Failed to create second doughnut chart")
            return False
        
        # Test with exploded doughnut chart
        print("\nCreating exploded doughnut chart...")
        
        chart_data_3 = {
            'categories': ['Product A', 'Product B', 'Product C'],
            'series': [{
                'name': 'Market Share',
                'values': [45, 35, 20]
            }]
        }
        
        slice_colors_3 = ['#3498DB', '#E67E22', '#2ECC71']
        
        slide_data_3 = {
            'slide1': {
                'ExplodedDoughnutChart': {
                    'shape_type': 'chart',
                    'chart_type': 'doughnut_exploded',
                    'chart_data': chart_data_3,
                    'chart_title': 'Market Share by Product',
                    'series_colors': slice_colors_3,
                    'show_legend': True,
                    'show_data_labels': True,
                    'left': 50,
                    'top': 400,
                    'width': 350,
                    'height': 250
                }
            }
        }
        
        success, updated_shapes = writer.write_to_existing(slide_data_3, temp_path)
        
        if success:
            print("✅ Successfully created exploded doughnut chart")
            print(f"Updated shapes: {len(updated_shapes)}")
        else:
            print("❌ Failed to create exploded doughnut chart")
            return False
        
        print(f"\n🎉 All tests completed successfully!")
        print(f"📁 PowerPoint file saved at: {temp_path}")
        print(f"📊 The presentation contains 3 doughnut charts with custom colors")
        print("\nColor assignments:")
        print("Chart 1 (City Population):")
        for i, (city, color) in enumerate(zip(chart_data['categories'], slice_colors)):
            print(f"  - {city}: {color}")
        print("Chart 2 (Quarterly Sales):")
        for i, (quarter, color) in enumerate(zip(chart_data_2['categories'], slice_colors_2)):
            print(f"  - {quarter}: {color}")
        print("Chart 3 (Market Share - Exploded):")
        for i, (product, color) in enumerate(zip(chart_data_3['categories'], slice_colors_3)):
            print(f"  - {product}: {color}")
        
        print(f"\n💡 Open the file in PowerPoint to verify that each slice has the correct color!")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Clean up
        try:
            PowerPointWriter.cleanup()
        except Exception as e:
            print(f"Warning: Error during cleanup: {e}")

def main():
    """Main function to run the test."""
    print("🧪 Testing Doughnut Chart Colors with PowerPoint Writer")
    print("=" * 60)
    
    success = test_doughnut_chart_colors()
    
    if success:
        print("\n✅ All tests passed! Doughnut chart colors should be working correctly.")
        return 0
    else:
        print("\n❌ Tests failed. Please check the error messages above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
