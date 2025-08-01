import os
import json
import win32com.client as win32
import pythoncom
import time
from powerpoint.editing.powerpoint_writer import PowerPointWriter

def create_base_presentation(output_filepath):
    """Create a base PowerPoint presentation with blank slides."""
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
        
        # Save the presentation
        presentation.SaveAs(os.path.abspath(output_filepath))
        print(f"✓ Created base presentation: {os.path.abspath(output_filepath)}")
        
        # DON'T close the presentation - keep it open
        # presentation.Close()
        # ppt_app.Quit()
        
        print("📌 PowerPoint application left open for inspection")
        
        return True
        
    except Exception as e:
        print(f"✗ Error creating base presentation: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        pythoncom.CoUninitialize()

def test_powerpoint_writer_step_by_step():
    """Test the PowerPointWriter with detailed step-by-step analysis."""
    
    output_file = "test_powerpoint_writer_detailed.pptx"
    
    # Create charts one at a time to isolate issues
    chart_configs = [
        {
            "name": "sales_chart_q1",
            "config": {
                "shape_type": "chart",
                "chart_type": "doughnut",
                "chart_title": "Q1 Product Sales Distribution",
                "left": 50,
                "top": 50,
                "width": 280,
                "height": 180,
                "show_legend": True,
                "chart_data": {
                    "categories": ["Laptops", "Phones", "Tablets"],
                    "series": [
                        {
                            "name": "Q1 Sales",
                            "values": [45, 35, 20]
                        }
                    ]
                }
            }
        },
        {
            "name": "sales_chart_q2", 
            "config": {
                "shape_type": "chart",
                "chart_type": "doughnut",
                "chart_title": "Q2 Product Sales Distribution",
                "left": 350,
                "top": 50,
                "width": 280,
                "height": 180,
                "show_legend": True,
                "chart_data": {
                    "categories": ["Laptops", "Phones", "Tablets"],
                    "series": [
                        {
                            "name": "Q2 Sales",
                            "values": [50, 30, 20]
                        }
                    ]
                }
            }
        },
        {
            "name": "market_share_chart",
            "config": {
                "shape_type": "chart",
                "chart_type": "doughnut",
                "chart_title": "Market Share Analysis",
                "left": 200,
                "top": 280,
                "width": 280,
                "height": 180,
                "show_legend": True,
                "chart_data": {
                    "categories": ["Our Company", "Competitor A", "Competitor B", "Others"],
                    "series": [
                        {
                            "name": "Market Share",
                            "values": [40, 25, 20, 15]
                        }
                    ]
                }
            }
        }
    ]
    
    print("=== Testing PowerPointWriter Step-by-Step ===")
    
    # Step 1: Create base presentation
    print(f"\n🔧 Step 1: Creating base presentation...")
    if not create_base_presentation(output_file):
        print("❌ Failed to create base presentation")
        return
    
    # Initialize PowerPointWriter once
    print(f"\n🔧 Step 2: Initializing PowerPointWriter...")
    try:
        writer = PowerPointWriter()
        print("✓ PowerPointWriter initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize PowerPointWriter: {e}")
        return
    
    # Create charts one by one
    successful_charts = []
    failed_charts = []
    
    for i, chart_info in enumerate(chart_configs, 1):
        chart_name = chart_info["name"]
        chart_config = chart_info["config"]
        
        print(f"\n🔧 Step {i+2}: Creating chart '{chart_name}'...")
        print(f"   Chart Type: {chart_config['chart_type']}")
        print(f"   Position: ({chart_config['left']}, {chart_config['top']})")
        print(f"   Size: {chart_config['width']}x{chart_config['height']}")
        print(f"   Categories: {chart_config['chart_data']['categories']}")
        print(f"   Values: {chart_config['chart_data']['series'][0]['values']}")
        
        # Create slide data for this single chart
        single_chart_data = {
            "slide1": {
                chart_name: chart_config
            }
        }
        
        try:
            # Attempt to create this chart
            success, updated_shapes = writer.write_to_existing(
                slide_data=single_chart_data,
                output_filepath=os.path.abspath(output_file)
            )
            
            if success and len(updated_shapes) > 0:
                print(f"   ✅ SUCCESS: Chart '{chart_name}' created")
                print(f"      - Updated shapes: {len(updated_shapes)}")
                
                # Analyze the created shape
                for shape_info in updated_shapes:
                    shape_name = shape_info.get('shape_name', 'Unknown')
                    properties = shape_info.get('properties_applied', [])
                    print(f"      - Shape '{shape_name}': {len(properties)} properties applied")
                    print(f"        Properties: {properties}")
                
                successful_charts.append(chart_name)
                
            else:
                print(f"   ❌ FAILED: Chart '{chart_name}' creation failed")
                print(f"      - Success: {success}")
                print(f"      - Updated shapes: {len(updated_shapes) if updated_shapes else 0}")
                failed_charts.append(chart_name)
            
            # Small delay between chart creations
            time.sleep(1)
            
        except Exception as e:
            print(f"   ❌ EXCEPTION: Chart '{chart_name}' failed with exception: {e}")
            failed_charts.append(chart_name)
            import traceback
            print("   📋 Full traceback:")
            traceback.print_exc()
    
    # Summary
    print(f"\n📊 === Final Summary ===")
    print(f"✅ Successful charts ({len(successful_charts)}): {successful_charts}")
    print(f"❌ Failed charts ({len(failed_charts)}): {failed_charts}")
    print(f"📁 Output file: {os.path.abspath(output_file)}")
    print(f"📌 PowerPoint application left open for manual inspection")
    
    # Manual verification instructions
    print(f"\n🔍 === Manual Verification Instructions ===")
    print("1. Check the PowerPoint application window (should still be open)")
    print("2. Look at the slide to see which charts were actually created")
    print("3. For each chart, verify:")
    print("   - Is it actually a doughnut chart (has a hole in the middle)?")
    print("   - Does it show the correct data/categories?")
    print("   - Does it have the correct title?")
    print("4. Compare with the console output above")
    
    return successful_charts, failed_charts

def analyze_chart_creation_pattern(successful_charts, failed_charts):
    """Analyze the pattern of successful vs failed chart creation."""
    print(f"\n🔬 === Chart Creation Pattern Analysis ===")
    
    total_charts = len(successful_charts) + len(failed_charts)
    success_rate = len(successful_charts) / total_charts * 100 if total_charts > 0 else 0
    
    print(f"📈 Success Rate: {success_rate:.1f}% ({len(successful_charts)}/{total_charts})")
    
    if len(successful_charts) > 0:
        print("✅ Successful Chart Patterns:")
        for chart in successful_charts:
            print(f"   - {chart}")
    
    if len(failed_charts) > 0:
        print("❌ Failed Chart Patterns:")
        for chart in failed_charts:
            print(f"   - {chart}")
    
    # Hypothesis about the first chart issue
    if len(successful_charts) > 0 and successful_charts[0] == "sales_chart_q1":
        print("\n💭 Hypothesis: First chart issue")
        print("   - You mentioned the first chart wasn't a proper doughnut")
        print("   - This could be due to chart type correction happening too late")
        print("   - Subsequent charts benefit from the chart type being 'warmed up'")
    
    print(f"\n⏳ Keeping PowerPoint open for 60 seconds for manual inspection...")
    print("   (The script will continue to run so you can inspect the charts)")
    
    # Keep the script alive so PowerPoint stays open
    for i in range(60, 0, -10):
        print(f"   Time remaining: {i} seconds...")
        time.sleep(10)
    
    print("🏁 Analysis complete!")

if __name__ == "__main__":
    successful_charts, failed_charts = test_powerpoint_writer_step_by_step()
    analyze_chart_creation_pattern(successful_charts, failed_charts)
