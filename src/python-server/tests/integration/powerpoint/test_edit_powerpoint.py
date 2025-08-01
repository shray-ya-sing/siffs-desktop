import os
import sys
sys.path.append(r'C:\Users\shrey\projects\cori-apps\cori_app\src\python-server')
from powerpoint.editing.powerpoint_writer import PowerPointWriter

def create_process_mapping_presentation(file_path):
    slide_data = {
        "slide6": {
            "_slide_layout": 5,
            "Title 1": {
                "text": "Process Mapping Template",
                "font_color": "#3A4D6A",
                "font_size": 36,
                "bold": True,
                "text_align": "left",
                "left": 48,
                "top": 27,
                "width": 864,
                "height": 55
            },
            "Row Header 1": {
                "geom": "rounded_rectangle",
                "fill": "#E8EBF0",
                "out_col": "none",
                "width": 144,
                "height": 108,
                "left": 48,
                "top": 216,
                "text": "Purpose",
                "font_name": "Calibri",
                "font_size": 16,
                "font_color": "#000000",
                "bold": True,
                "text_align": "center",
                "vertical_align": "middle"
            },
            "Row Header 2": {
                "geom": "rounded_rectangle",
                "fill": "#E8EBF0",
                "out_col": "none",
                "width": 144,
                "height": 108,
                "left": 48,
                "top": 333,
                "text": "Primary Tools",
                "font_name": "Calibri",
                "font_size": 16,
                "font_color": "#000000",
                "bold": True,
                "text_align": "center",
                "vertical_align": "middle"
            },
            "Row Header 3": {
                "geom": "rounded_rectangle",
                "fill": "#E8EBF0",
                "out_col": "none",
                "width": 144,
                "height": 108,
                "left": 48,
                "top": 450,
                "text": "Key Outputs",
                "font_name": "Calibri",
                "font_size": 16,
                "font_color": "#000000",
                "bold": True,
                "text_align": "center",
                "vertical_align": "middle"
            },
            "Content Column 1": {
                "geom": "rounded_rectangle",
                "fill": "#F2F5F9",
                "out_col": "none",
                "width": 144,
                "height": 442,
                "left": 207,
                "top": 116
            },
            "Content Column 2": {
                "geom": "rounded_rectangle",
                "fill": "#F2F5F9",
                "out_col": "none",
                "width": 144,
                "height": 442,
                "left": 360,
                "top": 116
            },
            "Content Column 3": {
                "geom": "rounded_rectangle",
                "fill": "#F2F5F9",
                "out_col": "none",
                "width": 144,
                "height": 442,
                "left": 513,
                "top": 116
            },
            "Content Column 4": {
                "geom": "rounded_rectangle",
                "fill": "#F2F5F9",
                "out_col": "none",
                "width": 144,
                "height": 442,
                "left": 666,
                "top": 116
            },
            "Content Column 5": {
                "geom": "rounded_rectangle",
                "fill": "#F2F5F9",
                "out_col": "none",
                "width": 144,
                "height": 442,
                "left": 819,
                "top": 116
            },
            "Process Arrow": {
                "geom": "chevron",
                "fill": "#4F81BD",
                "out_col": "none",
                "width": 765,
                "height": 45,
                "left": 202,
                "top": 175
            },
            "Icon Placeholder 1": {
                "geom": "rounded_rectangle",
                "fill": "#F2F5F9",
                "out_col": "none",
                "width": 130,
                "height": 54,
                "left": 214,
                "top": 120
            },
            "Icon Placeholder 2": {
                "geom": "rounded_rectangle",
                "fill": "#F2F5F9",
                "out_col": "none",
                "width": 130,
                "height": 54,
                "left": 367,
                "top": 120
            },
            "Icon Placeholder 3": {
                "geom": "rounded_rectangle",
                "fill": "#F2F5F9",
                "out_col": "none",
                "width": 130,
                "height": 54,
                "left": 520,
                "top": 120
            },
            "Icon Placeholder 4": {
                "geom": "rounded_rectangle",
                "fill": "#F2F5F9",
                "out_col": "none",
                "width": 130,
                "height": 54,
                "left": 673,
                "top": 120
            },
            "Icon Placeholder 5": {
                "geom": "rounded_rectangle",
                "fill": "#F2F5F9",
                "out_col": "none",
                "width": 130,
                "height": 54,
                "left": 826,
                "top": 120
            }
        }
    }
    
    try:
        print(f"Creating PowerPoint writer...")
        ppt_writer = PowerPointWriter()
        
        print(f"Writing shapes to PowerPoint file: {file_path}")
        success, updated_shapes = ppt_writer.write_to_existing(slide_data, file_path)
        
        if success:
            print(f"Successfully updated {len(updated_shapes)} shapes!")
            for shape_info in updated_shapes:
                print(f"  - {shape_info.get('shape_name', 'Unknown')} on slide {shape_info.get('slide_number', 'Unknown')}")
        else:
            print("Failed to update PowerPoint file")
            
    except Exception as e:
        print(f"Error occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    file_path = r"C:\Users\shrey\OneDrive\Desktop\docs\speed_it_up\2024.10.27 Project Core - Valuation Analysis_v22.pptx"
    
    # Check if file exists
    if not os.path.exists(file_path):
        print(f"Error: PowerPoint file not found at {file_path}")
        exit(1)
    
    print(f"Found PowerPoint file: {file_path}")
    create_process_mapping_presentation(file_path)

