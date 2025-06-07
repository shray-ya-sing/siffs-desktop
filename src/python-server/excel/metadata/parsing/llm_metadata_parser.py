import re
from typing import Dict, List, Any, Optional, Tuple, Set, Callable
from dataclasses import dataclass
from enum import Enum

class CellProperty(Enum):
    CELL_REF = "cell"
    FORMULA = "formula"
    FONT_STYLE = "font_style"
    FONT_SIZE = "font_size"
    BOLD = "bold"
    ITALIC = "italic"
    TEXT_COLOR = "text_color"
    HORIZONTAL_ALIGN = "horizontal_alignment"
    VERTICAL_ALIGN = "vertical_alignment"
    NUMBER_FORMAT = "number_format"
    FILL_COLOR = "fill_color"
    WRAP_TEXT = "wrap_text"

# Define valid values for enumerated types
VALID_ALIGNMENTS = {"left", "center", "right", "justify", "general"}
VALID_NUMBER_FORMATS = {"General", "0", "0.00", "#,##0", "#,##0.00", 
                       "0%", "0.00%", "0.00E+00", "# ?/?", "# ??/??",
                       "m/d/yyyy", "d-mmm-yy", "d-mmm", "mmm-yy"}



@dataclass
class ValidationResult:
    is_valid: bool
    value: Any
    error: Optional[str] = None

class LLMMetadataParser:
    """A robust metadata parser with comprehensive validation."""
    
    # Define property validators
    VALIDATORS: Dict[str, Callable[[Any], ValidationResult]] = {
        CellProperty.CELL_REF.value: lambda x: LLMMetadataParser._validate_cell_ref(x),
        CellProperty.FONT_SIZE.value: lambda x: LLMMetadataParser._validate_positive_int(x, 1, 72),
        CellProperty.BOLD.value: lambda x: LLMMetadataParser._validate_bool(x),
        CellProperty.ITALIC.value: lambda x: LLMMetadataParser._validate_bool(x),
        CellProperty.WRAP_TEXT.value: lambda x: LLMMetadataParser._validate_bool(x),
        CellProperty.TEXT_COLOR.value: lambda x: LLMMetadataParser._validate_hex_color(x),
        CellProperty.FILL_COLOR.value: lambda x: LLMMetadataParser._validate_hex_color(x, allow_none=True),
        CellProperty.HORIZONTAL_ALIGN.value: lambda x: LLMMetadataParser._validate_enum(x, VALID_ALIGNMENTS),
        CellProperty.VERTICAL_ALIGN.value: lambda x: LLMMetadataParser._validate_enum(x, VALID_ALIGNMENTS),
        CellProperty.NUMBER_FORMAT.value: lambda x: LLMMetadataParser._validate_enum(x, VALID_NUMBER_FORMATS, case_sensitive=False),
    }

    # Patterns for identifying valid metadata sections
    WORKSHEET_PATTERN = re.compile(
        r'worksheet\s*name\s*=\s*"([^"]+)"\s*\|\s*(.*?)(?=worksheet\s*name\s*=|$)',
        re.DOTALL | re.IGNORECASE
    )
    CELL_REF_PATTERN = re.compile(r'cell\s*=\s*"([^"]+)"')
    PROPERTY_PATTERN = re.compile(r'(\w+)\s*=\s*"([^"]*)"')

    @classmethod
    def parse(cls, metadata: Optional[str], strict: bool = True) -> Dict[str, List[Dict[str, Any]]]:
        """Parse and validate metadata with comprehensive error handling and text filtering."""
        if not metadata or not isinstance(metadata, str):
            return {}

        metadata = metadata.strip()
        if not metadata:
            return {}

        # First, extract only the metadata sections
        metadata_sections = cls._extract_metadata_sections(metadata)
        if not metadata_sections:
            if strict:
                raise ValueError("No valid metadata sections found in the input")
            return {}

        # Parse the cleaned metadata
        try:
            result = cls._parse_escaped_metadata('\n'.join(metadata_sections))
            if not result:
                result = cls._parse_simple_metadata('\n'.join(metadata_sections))
            
            return cls._validate_result(result, strict)

        except Exception as e:
            if strict:
                raise ValueError(f"Error parsing metadata: {str(e)}")
            return {}

    @classmethod
    def _extract_metadata_sections(cls, text: str) -> List[str]:
        """Extract only the valid metadata sections from potentially noisy text."""
        # Look for worksheet sections
        worksheet_matches = list(cls.WORKSHEET_PATTERN.finditer(text))
        if worksheet_matches:
            return [match.group(0) for match in worksheet_matches]
            
        # If no worksheet sections found, try to find cell definitions
        cell_defs = []
        lines = text.split('\n')
        current_section = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Check if line contains a cell definition
            if cls.CELL_REF_PATTERN.search(line):
                if current_section:  # If we have a pending section, add it
                    cell_defs.append(' | '.join(current_section))
                    current_section = []
                current_section.append(line)
            elif current_section:  # Continue current section
                # Only add lines that contain property definitions
                if '=' in line and any(c.isalpha() or c.isdigit() for c in line.split('=')[0].strip()):
                    current_section.append(line)
        
        # Add the last section if exists
        if current_section:
            cell_defs.append(' | '.join(current_section))
            
        return cell_defs

    @classmethod
    def _validate_result(cls, result: Dict[str, List[Dict[str, Any]]], strict: bool) -> Dict[str, List[Dict[str, Any]]]:
        """Validate the parsed result."""
        if not strict:
            return result
            
        validated_result = {}
        for sheet_name, cells in result.items():
            validated_cells = []
            for cell in cells:
                validated_cell = cls._validate_cell(cell)
                if validated_cell:
                    validated_cells.append(validated_cell)
            if validated_cells:
                validated_result[sheet_name] = validated_cells
                
        return validated_result

    @classmethod
    def _validate_cell(cls, cell_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Validate all properties of a cell."""
        if not cell_data or 'cell' not in cell_data:
            return None

        validated = {'cell': cell_data['cell']}
        
        for key, value in cell_data.items():
            if key == 'cell':
                continue
                
            # Normalize key
            norm_key = key.lower().replace(' ', '_')
            
            # Get validator if exists
            validator = cls.VALIDATORS.get(norm_key)
            if validator:
                result = validator(value)
                if result.is_valid:
                    validated[norm_key] = result.value
                # Optionally log or handle invalid values
            else:
                # For unknown properties, keep as-is
                validated[norm_key] = value
                
        return validated

    # Validation helper methods
    @staticmethod
    def _validate_cell_ref(value: Any) -> ValidationResult:
        """Validate cell reference (e.g., A1, B2, etc.)."""
        if not isinstance(value, str):
            return ValidationResult(False, None, "Cell reference must be a string")
            
        pattern = r'^[A-Za-z]{1,3}\d{1,7}$'
        if not re.match(pattern, str(value)):
            return ValidationResult(False, None, f"Invalid cell reference format: {value}")
        return ValidationResult(True, value.upper())

    @staticmethod
    def _validate_positive_int(value: Any, min_val: int = 1, max_val: int = 409) -> ValidationResult:
        """Validate positive integer within range."""
        try:
            num = int(value)
            if min_val <= num <= max_val:
                return ValidationResult(True, num)
            return ValidationResult(False, None, f"Value must be between {min_val} and {max_val}")
        except (ValueError, TypeError):
            return ValidationResult(False, None, "Invalid integer value")

    @staticmethod
    def _validate_bool(value: Any) -> ValidationResult:
        """Validate boolean value."""
        if isinstance(value, bool):
            return ValidationResult(True, value)
        if isinstance(value, str):
            if value.lower() in ('true', 't', 'yes', 'y', '1'):
                return ValidationResult(True, True)
            if value.lower() in ('false', 'f', 'no', 'n', '0', ''):
                return ValidationResult(True, False)
        return ValidationResult(False, None, "Invalid boolean value")

    @staticmethod
    def _validate_hex_color(value: Any, allow_none: bool = False) -> ValidationResult:
        """Validate hex color code."""
        if value is None and allow_none:
            return ValidationResult(True, None)
            
        if not isinstance(value, str):
            return ValidationResult(False, None, "Color must be a string")
            
        pattern = r'^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$'
        if re.match(pattern, value):
            return ValidationResult(True, value.upper())
        return ValidationResult(False, None, f"Invalid hex color code: {value}")

    @staticmethod
    def _validate_enum(value: Any, valid_values: Set[str], case_sensitive: bool = True) -> ValidationResult:
        """Validate value against a set of valid values."""
        if not isinstance(value, str):
            return ValidationResult(False, None, "Value must be a string")
            
        test_value = value if case_sensitive else value.lower()
        
        if case_sensitive:
            if test_value in valid_values:
                return ValidationResult(True, test_value)
        else:
            valid_dict = {v.lower(): v for v in valid_values}
            if test_value in valid_dict:
                return ValidationResult(True, valid_dict[test_value])
                
        return ValidationResult(False, None, f"Invalid value: {value}. Must be one of: {', '.join(valid_values)}")
    
    @classmethod
    def _parse_simple_metadata(cls, metadata: str) -> Dict[str, List[Dict[str, Any]]]:
        """Parse simple metadata format with enhanced robustness."""
        result = {}
        
        # Split into potential worksheet sections
        sections = re.split(r'worksheet\s*name\s*=\s*"([^"]+)"\s*\|', metadata, flags=re.IGNORECASE)
        
        # If no worksheet sections found, try to parse as a single worksheet
        if len(sections) == 1:
            return cls._parse_single_worksheet("Sheet1", sections[0].strip())
            
        # Process each worksheet section
        for i in range(1, len(sections), 2):
            if i + 1 >= len(sections):
                break
                
            sheet_name = sections[i].strip()
            cell_data_str = sections[i+1].strip()
            
            if not sheet_name or not cell_data_str:
                continue
                
            worksheet_data = cls._parse_single_worksheet(sheet_name, cell_data_str)
            if worksheet_data:
                result.update(worksheet_data)
                
        return result

    @classmethod
    def _parse_single_worksheet(cls, sheet_name: str, content: str) -> Dict[str, List[Dict[str, Any]]]:
        """Parse content for a single worksheet."""
        cells = []
        cell_definitions = [c.strip() for c in content.split('|') if c.strip()]
        
        for cell_def in cell_definitions:
            cell_ref_match = cls.CELL_REF_PATTERN.search(cell_def)
            if not cell_ref_match:
                continue
                
            cell_ref = cell_ref_match.group(1)
            cell_data = {'cell': cell_ref}
            valid_props = False
            
            for match in cls.PROPERTY_PATTERN.finditer(cell_def):
                key, value = match.groups()
                if key.lower() == 'cell':
                    continue
                    
                # Basic validation of property
                if not key.strip() or not value.strip():
                    continue
                    
                # Convert value types
                value = cls._convert_property_value(key, value)
                if value is not None:
                    cell_data[key.lower()] = value
                    valid_props = True
                    
            if valid_props:
                cells.append(cell_data)
                
        return {sheet_name: cells} if cells else {}

    @staticmethod
    def _convert_property_value(key: str, value: str) -> Any:
        """Convert string property values to appropriate Python types."""
        value = value.strip()
        
        # Handle boolean values
        if value.lower() in ('true', 'false'):
            return value.lower() == 'true'
            
        # Handle numeric values
        if value.replace('.', '', 1).isdigit():
            return float(value) if '.' in value else int(value)
            
        # Handle empty strings
        if not value:
            return None
            
        return value

    @classmethod
    def _parse_escaped_metadata(cls, metadata: str) -> Dict[str, List[Dict[str, Any]]]:
        """Parse metadata with semicolon-delimited properties with enhanced robustness."""
        result = {}
        
        # Process each worksheet section
        for match in cls.WORKSHEET_PATTERN.finditer(metadata):
            sheet_name = match.group(1).strip()
            cell_data_str = match.group(2).strip()
            
            if not sheet_name:
                continue
                
            # Process cell definitions
            cell_definitions = [c.strip() for c in cell_data_str.split('|') if c.strip()]
            cells = []
            
            for cell_def in cell_definitions:
                cell_ref_match = cls.CELL_REF_PATTERN.search(cell_def)
                if not cell_ref_match:
                    continue
                    
                cell_ref = cell_ref_match.group(1)
                cell_data = {'cell': cell_ref}
                valid_props = False
                
                # Process each property in the cell definition
                for prop in cell_def.split(';'):
                    prop = prop.strip()
                    if '=' not in prop:
                        continue
                        
                    key_value = [p.strip() for p in prop.split('=', 1)]
                    if len(key_value) != 2:
                        continue
                        
                    key, value = key_value
                    key = key.strip().lower()
                    
                    if key == 'cell':
                        continue
                        
                    value = value.strip().strip('"\'')
                    value = cls._convert_property_value(key, value)
                    
                    if value is not None:
                        cell_data[key] = value
                        valid_props = True
                        
                if valid_props:
                    cells.append(cell_data)
                    
            if cells:
                result[sheet_name] = cells
                
        return result