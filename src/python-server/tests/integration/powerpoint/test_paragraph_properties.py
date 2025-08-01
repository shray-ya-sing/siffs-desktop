import pytest
import os
from pathlib import Path
from pythoncom import CoInitialize, CoUninitialize
from win32com.client import Dispatch
from editing.powerpoint_writer import PowerPointWriter

@pytest.fixture(scope="module")
def setup_presentation():
    CoInitialize()
    writer = PowerPointWriter()
    output_path = Path("test_presentation.pptx").resolve()
    writer.add_blank_slide(str(output_path))
    yield str(output_path)
    CoUninitialize()
    
@pytest.mark.parametrize("shape_data, expected_properties", [
    ({
        "slide1": {
            "Test Text Box": {
                "text": "This is a test\nWith multiple lines",
                "indent_level": 2,
                "bullet_style": "bullet",
                "bullet_char": "-",
                "left_indent": 20.0,
                "right_indent": 10.0,
                "first_line_indent": 5.0,
                "space_before": 10,
                "space_after": 15
            }
        }
    }, [
        'indent_level', 'bullet_style', 'bullet_char', 'left_indent',
        'right_indent', 'first_line_indent', 'space_before', 'space_after'
    ])
])
def test_paragraph_properties(setup_presentation, shape_data, expected_properties):
    output_path = setup_presentation
    writer = PowerPointWriter()
    success, updated_shapes = writer.write_to_existing(shape_data, output_path)
    assert success, "Failed to write to presentation"
    
    updated_properties = updated_shapes[0]['properties_applied']
    for prop in expected_properties:
        assert prop in updated_properties, f"{prop} not applied"

    # Cleanup
    try:
        os.remove(output_path)
    except OSError:
        pass
