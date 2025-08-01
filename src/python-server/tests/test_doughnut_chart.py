#!/usr/bin/env python3
"""
Test script to create doughnut charts using PowerPointWriter
"""
import os
import sys
import tempfile
from pathlib import Path

# Add the parent directory to sys.path to import powerpoint_writer
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from powerpoint.editing.powerpoint_writer import PowerPointWriter

def test_doughnut_chart_creation():
    """Test creating doughnut charts with mock data"""
    
    print("=== TESTING DOUGHNUT CHART CREATION ===")
    
    # Create a temporary PowerPoint file
    with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as tmp_file:
        temp_pptx_path = tmp_file.name
    
    try:
        # Create a basic PowerPoint file first
        print(f"1. Creating temporary PowerPoint file: {temp_pptx_path}")
        
        # Initialize PowerPoint writer
        writer = PowerPointWriter()
        
        # Add a blank slide first
        success = writer.add_blank_slide(temp_pptx_path, 1)
        if not success:
            print("   ❌ FAILED: Could not add blank slide")
            return False
        
        print("   ✅ Successfully added blank slide")
        
        # Test data for doughnut chart
        mock_chart_data = {
            'categories': ['Toronto', 'Calgary', 'Ottawa', 'Vancouver'],
            'series': [
                {
                    'name': 'Sales',
                    'values': [51, 39, 10, 25]
                }
            ]
        }
        
        # Create slide data with doughnut chart
        slide_data = {
            'slide1': {
                'DoughnutChart1': {
                    'shape_type': 'chart',
                    'chart_type': 'doughnut',
                    'chart_data': mock_chart_data,
                    'chart_title': 'Sales by City (Doughnut Chart)',
                    'left': 100,
                    'top': 100,
                    'width': 400,
                    'height': 300,
                    'show_legend': True,
                    'show_data_labels': True,
                    'series_colors': ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4']
                }
            }
        }
        
        print("2. Creating doughnut chart with mock data...")
        print(f"   Chart data: {mock_chart_data}")
        
        # Write the chart to PowerPoint
        success, updated_shapes = writer.write_to_existing(slide_data, temp_pptx_path)
        
        if success:
            print("   ✅ SUCCESS: Doughnut chart created successfully!")
            print(f"   Updated {len(updated_shapes)} shapes")
            
            # Print details of created shapes
            for shape_info in updated_shapes:
                print(f"   Shape: {shape_info.get('shape_name', 'Unknown')}")
                print(f"   Properties applied: {shape_info.get('properties_applied', [])}")
        else:
            print("   ❌ FAILED: Could not create doughnut chart")
            return False
        
        # Test with different doughnut chart data
        print("\n3. Creating second doughnut chart with different data...")
        
        mock_chart_data_2 = {
            'categories': ['Q1', 'Q2', 'Q3', 'Q4'],
            'series': [
                {
                    'name': 'Revenue',
                    'values': [120000, 135000, 128000, 142000]
                }
            ]
        }
        
        slide_data_2 = {
            'slide1': {
                'DoughnutChart2': {
                    'shape_type': 'chart',
                    'chart_type': 'doughnut',
                    'chart_data': mock_chart_data_2,
                    'chart_title': 'Quarterly Revenue (Doughnut)',
                    'left': 520,
                    'top': 100,
                    'width': 350,
                    'height': 300,
                    'show_legend': True,
                    'show_data_labels': True,
                    'data_label_font_size': 12,
                    'legend_position': 'bottom',
                    'series_colors': ['#E74C3C', '#F39C12', '#27AE60', '#3498DB']
                }
            }
        }
        
        success_2, updated_shapes_2 = writer.write_to_existing(slide_data_2, temp_pptx_path)
        
        if success_2:
            print("   ✅ SUCCESS: Second doughnut chart created successfully!")
            print(f"   Updated {len(updated_shapes_2)} additional shapes")
        else:
            print("   ❌ FAILED: Could not create second doughnut chart")
            return False
        
        # Test with 2D array format data
        print("\n4. Testing with 2D array format data...")
        
        array_chart_data = [
            ['', 'Market Share'],
            ['Product A', 35],
            ['Product B', 25],
            ['Product C', 20],
            ['Product D', 15],
            ['Others', 5]
        ]
        
        slide_data_3 = {
            'slide1': {
                'DoughnutChart3': {
                    'shape_type': 'chart',
                    'chart_type': 'doughnut',
                    'chart_data': array_chart_data,
                    'chart_title': 'Market Share Distribution',
                    'left': 100,
                    'top': 420,
                    'width': 400,
                    'height': 250,
                    'show_legend': True,
                    'legend_position': 'right',
                    'series_colors': ['#9B59B6', '#E67E22', '#1ABC9C', '#F1C40F', '#95A5A6']
                }
            }
        }
        
        success_3, updated_shapes_3 = writer.write_to_existing(slide_data_3, temp_pptx_path)
        
        if success_3:
            print("   ✅ SUCCESS: Third doughnut chart (2D array format) created successfully!")
        else:
            print("   ❌ FAILED: Could not create third doughnut chart")
            return False
        
        print(f"\n5. Final PowerPoint file saved at: {temp_pptx_path}")
        print("   You can open this file to verify the doughnut charts were created correctly")
        
        # Don't delete the file so we can inspect it
        print(f"   File kept for inspection: {temp_pptx_path}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Clean up PowerPoint writer
        try:
            PowerPointWriter.cleanup()
        except:
            pass

def test_doughnut_exploded_chart():
    """Test creating exploded doughnut charts"""
    
    print("\n=== TESTING EXPLODED DOUGHNUT CHART ===")
    
    # Create a temporary PowerPoint file
    with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as tmp_file:
        temp_pptx_path = tmp_file.name
    
    try:
        writer = PowerPointWriter()
        
        # Add a blank slide
        success = writer.add_blank_slide(temp_pptx_path, 1)
        if not success:
            print("   ❌ FAILED: Could not add blank slide")
            return False
        
        # Create exploded doughnut chart data
        exploded_chart_data = {
            'categories': ['Desktop', 'Mobile', 'Tablet', 'Smart TV'],
            'series': [
                {
                    'name': 'Device Usage',
                    'values': [45, 35, 15, 5]
                }
            ]
        }
        
        slide_data = {
            'slide1': {
                'ExplodedDoughnut': {
                    'shape_type': 'chart',
                    'chart_type': 'doughnut_exploded',
                    'chart_data': exploded_chart_data,
                    'chart_title': 'Device Usage Distribution (Exploded)',
                    'left': 150,
                    'top': 150,
                    'width': 450,
                    'height': 350,
                    'show_legend': True,
                    'show_data_labels': True,
                    'legend_position': 'bottom',
                    'series_colors': ['#FF5733', '#33FF57', '#3357FF', '#FF33F5']
                }
            }
        }
        
        success, updated_shapes = writer.write_to_existing(slide_data, temp_pptx_path)
        
        if success:
            print("   ✅ SUCCESS: Exploded doughnut chart created successfully!")
            print(f"   File saved at: {temp_pptx_path}")
            return True
        else:
            print("   ❌ FAILED: Could not create exploded doughnut chart")
            return False
            
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
        return False
    
    finally:
        try:
            PowerPointWriter.cleanup()
        except:
            pass

if __name__ == "__main__":
    print("Starting doughnut chart tests...\n")
    
    # Test regular doughnut charts
    result1 = test_doughnut_chart_creation()
    
    # Test exploded doughnut charts
    result2 = test_doughnut_exploded_chart()
    
    print("\n" + "="*50)
    print("FINAL RESULTS:")
    print(f"Regular doughnut charts: {'✅ PASSED' if result1 else '❌ FAILED'}")
    print(f"Exploded doughnut charts: {'✅ PASSED' if result2 else '❌ FAILED'}")
    
    if result1 and result2:
        print("\n🎉 ALL TESTS PASSED! Doughnut chart creation is working correctly.")
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")
