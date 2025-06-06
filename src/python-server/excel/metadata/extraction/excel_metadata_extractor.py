import os
import json
import traceback
import re
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime
from collections import defaultdict

# Handle import errors gracefully
try:
    import openpyxl
    from openpyxl.styles import Font, Fill, Border, Alignment
    from openpyxl.utils import get_column_letter
    OPENPYXL_AVAILABLE = True
except ImportError as e:
    OPENPYXL_AVAILABLE = False
    print(f"Warning: openpyxl import failed - Excel metadata extraction will not be available: {str(e)}")

try:
    import xlwings as xw
    XLWINGS_AVAILABLE = True
except ImportError:
    XLWINGS_AVAILABLE = False
    print("Warning: xlwings not available - display values will not be extracted")

class ExcelDependencyExtractor:
    """Helper class for extracting cell dependencies from Excel formulas"""
    
    def __init__(self):
        self.dependency_map = defaultdict(set)  # cell -> cells it depends on
        self.dependent_map = defaultdict(set)   # cell -> cells that depend on it
    
    def column_string_to_number(self, col_str):
        """Convert column string (A, B, ..., AA, AB, etc.) to number"""
        num = 0
        for char in col_str:
            num = num * 26 + (ord(char.upper()) - ord('A') + 1)
        return num
    
    def number_to_column_string(self, col_num):
        """Convert column number to string (1->A, 2->B, ..., 27->AA, etc.)"""
        result = ""
        while col_num > 0:
            col_num -= 1
            result = chr(col_num % 26 + ord('A')) + result
            col_num //= 26
        return result
    
    def parse_cell_address(self, cell_ref):
        """Parse cell address like 'A1', '$A$1', 'A$1', '$A1' into (column, row)"""
        clean_ref = cell_ref.replace('$', '')
        match = re.match(r'^([A-Z]+)(\d+)$', clean_ref.upper())
        if match:
            col_str, row_str = match.groups()
            col_num = self.column_string_to_number(col_str)
            row_num = int(row_str)
            return col_num, row_num
        return None, None
    
    def extract_ranges_and_expand(self, formula, current_sheet):
        """Extract cell ranges (with colons) and expand them to individual cells"""
        if not formula or not formula.startswith('='):
            return set(), formula
        
        expanded_cells = set()
        modified_formula = formula
        
        # Pattern to match ranges with optional sheet references
        range_pattern = r"(?:(?:'([^']+)'|([^'!\s(),\+\-\*/]+))!)?(\$?[A-Z]+\$?\d+):(\$?[A-Z]+\$?\d+)"
        
        range_matches = re.finditer(range_pattern, formula.upper())
        
        for match in range_matches:
            quoted_sheet, unquoted_sheet, start_cell, end_cell = match.groups()
            sheet_name = quoted_sheet or unquoted_sheet or current_sheet
            
            start_col, start_row = self.parse_cell_address(start_cell)
            end_col, end_row = self.parse_cell_address(end_cell)
            
            if None in (start_col, start_row, end_col, end_row):
                continue
            
            # Ensure start <= end
            if start_col > end_col:
                start_col, end_col = end_col, start_col
            if start_row > end_row:
                start_row, end_row = end_row, start_row
            
            # Limit range expansion to prevent memory issues
            max_cells = 10000  # Adjust as needed
            range_size = (end_row - start_row + 1) * (end_col - start_col + 1)
            
            if range_size > max_cells:
                print(f"Warning: Range {start_cell}:{end_cell} too large ({range_size} cells), skipping expansion")
                continue
            
            # Expand the range
            for row in range(start_row, end_row + 1):
                for col in range(start_col, end_col + 1):
                    col_str = self.number_to_column_string(col)
                    cell_addr = f"{sheet_name}!{col_str}{row}"
                    expanded_cells.add(cell_addr)
            
            # Remove this range from the formula
            full_range = match.group(0)
            modified_formula = modified_formula.replace(full_range, f"__RANGE_PLACEHOLDER_{len(expanded_cells)}__", 1)
        
        return expanded_cells, modified_formula
    
    def extract_individual_cells(self, formula, current_sheet):
        """Extract individual cell references (not ranges) from formula"""
        if not formula or not formula.startswith('='):
            return set()
        
        individual_cells = set()
        cell_pattern = r"(?:(?:'([^']+)'|([^'!\s(),\+\-\*/]+))!)?(\$?[A-Z]+\$?\d+)(?!:)"
        
        cell_matches = re.finditer(cell_pattern, formula.upper())
        
        for match in cell_matches:
            quoted_sheet, unquoted_sheet, cell_ref = match.groups()
            sheet_name = quoted_sheet or unquoted_sheet or current_sheet
            
            col, row = self.parse_cell_address(cell_ref)
            if col is not None and row is not None:
                cell_addr = f"{sheet_name}!{self.number_to_column_string(col)}{row}"
                individual_cells.add(cell_addr)
        
        return individual_cells
    
    def extract_all_cell_references(self, formula, current_sheet):
        """Extract all cell references from formula: ranges + individual cells"""
        if not formula or not formula.startswith('='):
            return set()
        
        all_references = set()
        
        try:
            # Extract and expand ranges
            range_cells, modified_formula = self.extract_ranges_and_expand(formula, current_sheet)
            all_references.update(range_cells)
            
            # Extract individual cells
            individual_cells = self.extract_individual_cells(modified_formula, current_sheet)
            all_references.update(individual_cells)
        except Exception as e:
            print(f"Warning: Error extracting references from formula '{formula}': {str(e)}")
        
        return all_references
    
    def build_dependency_maps(self, all_cells_metadata):
        """Build complete dependency maps from all cell metadata"""
        print("Building dependency maps...")
        
        # Reset maps
        self.dependency_map.clear()
        self.dependent_map.clear()
        
        formula_count = 0
        total_dependencies = 0
        
        for cell_address, cell_data in all_cells_metadata.items():
            formula = cell_data.get('formula')
            if not formula:
                continue
            
            formula_count += 1
            sheet_name = cell_data.get('sheet', cell_address.split('!')[0] if '!' in cell_address else 'Sheet1')
            
            # Extract all cell references
            try:
                precedents = self.extract_all_cell_references(formula, sheet_name)
                
                # Build bidirectional mapping
                for precedent in precedents:
                    self.dependency_map[cell_address].add(precedent)
                    self.dependent_map[precedent].add(cell_address)
                
                total_dependencies += len(precedents)
                
            except Exception as e:
                print(f"Warning: Error processing dependencies for {cell_address}: {str(e)}")
                continue
        
        print(f"Built dependency maps for {formula_count} formula cells with {total_dependencies} total dependencies")
        return self.dependency_map, self.dependent_map

class ExcelMetadataExtractor:
    def __init__(self, workbook_path: Optional[str] = None):
        """
        Initialize the metadata extractor with enhanced error handling and dependency extraction.
        
        Args:
            workbook_path: Path to the Excel file (optional, can be set later)
        """
        if not OPENPYXL_AVAILABLE:
            raise ImportError("openpyxl is required but not installed. Please install with: pip install openpyxl")
            
        self.workbook_path = None
        self.workbook = None
        self.workbook_values = None
        self.xlwings_extractor = None
        self.dependency_extractor = ExcelDependencyExtractor()
        self._initialize_xlwings()
        
        if workbook_path:
            self.open_workbook(workbook_path)

    def _initialize_xlwings(self) -> None:
        """Initialize xlwings extractor if available."""
        if not XLWINGS_AVAILABLE:
            print("Warning: xlwings not available - display values will not be extracted")
            return
            
        try:
            from .xlwings_extractor import XlwingsMetadataExtractor
            self.xlwings_extractor = XlwingsMetadataExtractor()
        except ImportError as e:
            print(f"Warning: Failed to initialize xlwings extractor: {str(e)}")
        except Exception as e:
            print(f"Warning: Unexpected error initializing xlwings: {str(e)}")
            print(traceback.format_exc())

    def open_workbook(self, workbook_path: Optional[str] = None) -> None:
        """Open the Excel workbook with comprehensive error handling."""
        try:
            if workbook_path:
                self.workbook_path = os.path.abspath(workbook_path)
                
            if not self.workbook_path:
                raise ValueError("No workbook path specified")
                
            if not os.path.exists(self.workbook_path):
                raise FileNotFoundError(f"Workbook not found: {self.workbook_path}")
                
            if not os.path.isfile(self.workbook_path):
                raise ValueError(f"Path is not a file: {self.workbook_path}")
                
            # Open workbooks with explicit error handling
            try:
                self.workbook = openpyxl.load_workbook(
                    self.workbook_path, 
                    data_only=False,
                    read_only=True,
                    keep_links=False
                )
            except Exception as e:
                raise RuntimeError(f"Failed to open workbook for formulas: {str(e)}")
                
            try:
                self.workbook_values = openpyxl.load_workbook(
                    self.workbook_path,
                    data_only=True,
                    read_only=True,
                    keep_links=False
                )
            except Exception as e:
                if self.workbook:
                    self.workbook.close()
                    self.workbook = None
                raise RuntimeError(f"Failed to open workbook for values: {str(e)}")
                
        except Exception as e:
            self.close()
            raise RuntimeError(f"Error opening workbook: {str(e)}") from e

    def close(self) -> None:
        """Safely close all open workbooks and clean up resources."""
        try:
            if self.workbook:
                self.workbook.close()
        except Exception as e:
            print(f"Warning: Error closing workbook: {str(e)}")
        finally:
            self.workbook = None
            
        try:
            if self.workbook_values:
                self.workbook_values.close()
        except Exception as e:
            print(f"Warning: Error closing values workbook: {str(e)}")
        finally:
            self.workbook_values = None

    def __enter__(self):
        """Context manager entry."""
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensures resources are cleaned up."""
        self.close()
        return False  # Don't suppress exceptions

    def extract_workbook_metadata(
        self,
        workbook_path: Optional[str] = None,
        output_path: Optional[str] = None,
        max_rows_per_sheet: int = 100,
        max_cols_per_sheet: int = 50,
        include_display_values: bool = False,
        include_dependencies: bool = True
    ) -> Tuple[Dict[str, Any], Dict[str, str]]:
        """
        Extract metadata with comprehensive error handling and dependency analysis.
        """
        try:
            # Get metadata using openpyxl
            metadata = self.extract_workbook_metadata_openpyxl(
                workbook_path,
                max_rows_per_sheet,
                max_cols_per_sheet,
                include_dependencies
            )
            
            # Get display values if requested and xlwings is available
            display_values = {}
            if include_display_values and self.xlwings_extractor:
                try:
                    display_values = self.xlwings_extractor._extract_display_values_xlwings(
                        workbook_path or self.workbook_path,
                        metadata
                    )
                except Exception as e:
                    print(f"Warning: Failed to extract display values: {str(e)}")
                    display_values = {"error": str(e)}
            
            return metadata, display_values
            
        except Exception as e:
            error_msg = f"Failed to extract workbook metadata: {str(e)}"
            print(error_msg)
            print(traceback.format_exc())
            raise RuntimeError(error_msg) from e

    def extract_workbook_metadata_openpyxl(
        self,
        workbook_path: Optional[str] = None,
        max_rows_per_sheet: int = 100,
        max_cols_per_sheet: int = 50,
        include_dependencies: bool = True
    ) -> Dict[str, Any]:
        """
        Extract metadata using openpyxl with comprehensive error handling and dependency analysis.
        """
        try:
            if workbook_path or not self.workbook:
                self.open_workbook(workbook_path)
                
            if not self.workbook:
                raise RuntimeError("Workbook is not open")
                
            # Get basic workbook info
            workbook_metadata = {
                "extractedAt": datetime.now().isoformat(),
                "workbookPath": self.workbook_path,
                "workbookName": os.path.basename(self.workbook_path) if self.workbook_path else "Unknown",
                "activeSheet": self.workbook.active.title if self.workbook.active else None,
                "totalSheets": len(self.workbook.worksheets),
                "sheetNames": [sheet.title for sheet in self.workbook.worksheets],
                "themeColors": self._get_theme_colors(),
                "sheets": [],
                "includeDependencies": include_dependencies
            }
            
            # First pass: Extract all cell metadata (without dependencies)
            all_cells_metadata = {}
            
            # Extract metadata for each sheet
            for sheet in self.workbook.worksheets:
                try:
                    sheet_metadata, sheet_cells = self._extract_sheet_metadata_with_cells(
                        sheet,
                        max_rows_per_sheet,
                        max_cols_per_sheet
                    )
                    workbook_metadata["sheets"].append(sheet_metadata)
                    
                    # Collect all cells for dependency analysis
                    all_cells_metadata.update(sheet_cells)
                    
                except Exception as e:
                    error_msg = f"Error processing sheet '{sheet.title}': {str(e)}"
                    print(f"Warning: {error_msg}")
                    print(traceback.format_exc())
                    workbook_metadata["sheets"].append({
                        "name": sheet.title,
                        "error": error_msg,
                        "isEmpty": True
                    })
            
            # Second pass: Build dependency relationships if requested
            if include_dependencies and all_cells_metadata:
                print("Building dependency relationships...")
                try:
                    dependency_map, dependent_map = self.dependency_extractor.build_dependency_maps(all_cells_metadata)
                    
                    # Third pass: Update all cells with dependency information
                    self._update_cells_with_dependencies(
                        workbook_metadata,
                        all_cells_metadata,
                        dependency_map,
                        dependent_map
                    )
                    
                    # Add dependency summary
                    self._add_dependency_summary(workbook_metadata, dependency_map, dependent_map, all_cells_metadata)
                    
                except Exception as e:
                    error_msg = f"Error building dependencies: {str(e)}"
                    print(f"Warning: {error_msg}")
                    workbook_metadata["dependencyError"] = error_msg
            
            return workbook_metadata
            
        except Exception as e:
            error_msg = f"Failed to extract workbook metadata: {str(e)}"
            print(error_msg)
            print(traceback.format_exc())
            raise RuntimeError(error_msg) from e

    def _extract_sheet_metadata_with_cells(
        self,
        sheet,
        max_rows: int,
        max_cols: int
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Extract metadata from a single sheet and return both sheet metadata and cell dictionary.
        """
        sheet_metadata = {
            "name": sheet.title,
            "error": None,
            "isEmpty": True,
            "rowCount": 0,
            "columnCount": 0,
            "cellData": [],
            "tables": [],
            "namedRanges": []
        }
        
        sheet_cells = {}  # For dependency analysis: {full_address: cell_metadata}
        
        try:
            # Get actual dimensions
            actual_row_count = min(sheet.max_row or 0, 1048576)  # Excel max rows
            actual_col_count = min(sheet.max_column or 0, 16384)  # Excel max columns
            
            # Check if sheet is empty
            if actual_row_count == 0 or actual_col_count == 0:
                sheet_metadata["isEmpty"] = True
                return sheet_metadata, sheet_cells
                
            sheet_metadata.update({
                "isEmpty": False,
                "rowCount": actual_row_count,
                "columnCount": actual_col_count,
                "extractedRowCount": min(actual_row_count, max_rows),
                "extractedColumnCount": min(actual_col_count, max_cols)
            })
            
            # Extract cell data
            try:
                sheet_metadata["cellData"], sheet_cells = self._extract_cell_data_with_addresses(
                    sheet,
                    sheet_metadata["extractedRowCount"],
                    sheet_metadata["extractedColumnCount"]
                )
            except Exception as e:
                sheet_metadata["error"] = f"Error extracting cell data: {str(e)}"
                print(f"Warning: {sheet_metadata['error']}")
                print(traceback.format_exc())
                sheet_metadata["cellData"] = []
            
            # Extract tables and named ranges
            try:
                sheet_metadata["tables"] = self._extract_tables_metadata(sheet)
            except Exception as e:
                sheet_metadata["error"] = sheet_metadata.get("error", "") + f" Tables: {str(e)}"
                print(f"Warning: Error extracting tables: {str(e)}")
                sheet_metadata["tables"] = []

            # TODO: Extract named ranges
            
            return sheet_metadata, sheet_cells
            
        except Exception as e:
            error_msg = f"Critical error extracting sheet '{sheet.title}': {str(e)}"
            print(error_msg)
            print(traceback.format_exc())
            sheet_metadata.update({
                "error": error_msg,
                "isEmpty": True
            })
            return sheet_metadata, sheet_cells

    def _extract_cell_data_with_addresses(
        self,
        sheet,
        row_count: int,
        col_count: int
    ) -> Tuple[List[List[Dict[str, Any]]], Dict[str, Any]]:
        """
        Extract cell data and return both 2D array and address-keyed dictionary.
        """
        cell_data = []
        cell_dict = {}  # For dependency analysis
        
        try:
            for row_idx in range(1, row_count + 1):
                row_data = []
                
                for col_idx in range(1, col_count + 1):
                    try:
                        cell = sheet.cell(row=row_idx, column=col_idx)
                        cell_metadata = self._extract_complete_cell_metadata(cell, row_idx, col_idx, sheet.title)
                        row_data.append(cell_metadata)
                        
                        # Add to dictionary for dependency analysis if has content
                        if cell_metadata.get('value') is not None or cell_metadata.get('formula'):
                            full_address = f"{sheet.title}!{cell_metadata['address']}"
                            cell_dict[full_address] = cell_metadata
                            
                    except Exception as e:
                        print(f"Warning: Error processing cell ({row_idx},{col_idx}): {str(e)}")
                        row_data.append({
                            "row": row_idx,
                            "column": col_idx,
                            "address": f"{get_column_letter(col_idx)}{row_idx}",
                            "error": str(e)
                        })
                
                cell_data.append(row_data)
                
        except Exception as e:
            print(f"Error extracting cell data: {str(e)}")
            print(traceback.format_exc())
            raise
            
        return cell_data, cell_dict

    def _extract_complete_cell_metadata(
        self,
        cell,
        row: int,
        col: int,
        sheet_name: str
    ) -> Dict[str, Any]:
        """
        Extract complete cell metadata including dependency placeholders.
        """
        try:
            # Handle EmptyCell objects
            if hasattr(cell, '__class__') and cell.__class__.__name__ == 'EmptyCell':
                return {
                    "row": row,
                    "column": col,
                    "address": f"{get_column_letter(col)}{row}",
                    "sheet": sheet_name,
                    "value": None,
                    "formula": None,
                    "formatting": {},
                    # Dependency information (will be filled later)
                    "directPrecedents": [],
                    "directDependents": [],
                    "precedentCount": 0,
                    "dependentCount": 0,
                    "totalConnections": 0
                }
                
            # Get corresponding cell from values workbook
            value_sheet = self.workbook_values[cell.parent.title]
            value_cell = value_sheet.cell(row=row, column=col)
            
            cell_metadata = {
                "row": row,
                "column": col,
                "address": f"{get_column_letter(col)}{row}",
                "sheet": sheet_name,
                "value": self._serialize_value(value_cell.value),
                "formula": self._get_cell_formula(cell),
                "formatting": self._extract_complete_cell_formatting(cell),
                # Dependency information (will be filled later)
                "directPrecedents": [],
                "directDependents": [],
                "precedentCount": 0,
                "dependentCount": 0,
                "totalConnections": 0
            }
            
            return cell_metadata
            
        except Exception as e:
            print(f"Error extracting metadata for cell ({row},{col}): {str(e)}")
            print(traceback.format_exc())
            return {
                "row": row,
                "column": col,
                "address": f"{get_column_letter(col)}{row}",
                "sheet": sheet_name,
                "error": str(e),
                # Dependency information
                "directPrecedents": [],
                "directDependents": [],
                "precedentCount": 0,
                "dependentCount": 0,
                "totalConnections": 0
            }

    def _update_cells_with_dependencies(
        self,
        workbook_metadata: Dict[str, Any],
        all_cells_metadata: Dict[str, Any],
        dependency_map: Dict[str, set],
        dependent_map: Dict[str, set]
    ):
        """Update all cells in workbook metadata with dependency information."""
        print("Updating cells with dependency information...")
        
        for sheet_data in workbook_metadata["sheets"]:
            if sheet_data.get("isEmpty") or "cellData" not in sheet_data:
                continue
                
            sheet_name = sheet_data["name"]
            
            for row_data in sheet_data["cellData"]:
                for cell_metadata in row_data:
                    if "address" in cell_metadata:
                        full_address = f"{sheet_name}!{cell_metadata['address']}"
                        
                        # Get dependency information
                        precedents = dependency_map.get(full_address, set())
                        dependents = dependent_map.get(full_address, set())
                        
                        # Update cell metadata
                        cell_metadata.update({
                            "directPrecedents": list(precedents),
                            "directDependents": list(dependents),
                            "precedentCount": len(precedents),
                            "dependentCount": len(dependents),
                            "totalConnections": len(precedents) + len(dependents)
                        })

    def _add_dependency_summary(
        self,
        workbook_metadata: Dict[str, Any],
        dependency_map: Dict[str, set],
        dependent_map: Dict[str, set],
        all_cells_metadata: Dict[str, Any]
    ):
        """Add dependency summary to workbook metadata."""
        
        total_cells = len(all_cells_metadata)
        formula_cells = sum(1 for data in all_cells_metadata.values() if data.get('formula'))
        total_dependencies = sum(len(deps) for deps in dependency_map.values())
        
        # Find most connected cells
        cell_connections = {}
        for cell_addr in all_cells_metadata:
            precedent_count = len(dependency_map.get(cell_addr, set()))
            dependent_count = len(dependent_map.get(cell_addr, set()))
            cell_connections[cell_addr] = precedent_count + dependent_count
        
        most_connected = sorted(cell_connections.items(), key=lambda x: x[1], reverse=True)[:10]
        most_precedents = sorted(
            [(cell, len(deps)) for cell, deps in dependency_map.items()],
            key=lambda x: x[1], reverse=True
        )[:10]
        most_dependents = sorted(
            [(cell, len(deps)) for cell, deps in dependent_map.items()],
            key=lambda x: x[1], reverse=True
        )[:10]
        
        # Add summary
        workbook_metadata["dependencySummary"] = {
            "totalCells": total_cells,
            "formulaCells": formula_cells,
            "valueCells": total_cells - formula_cells,
            "totalDependencies": total_dependencies,
            "avgDependenciesPerCell": total_dependencies / total_cells if total_cells > 0 else 0,
            "mostConnectedCells": [{"cell": cell, "connections": count} for cell, count in most_connected if count > 0],
            "mostComplexFormulas": [{"cell": cell, "precedents": count} for cell, count in most_precedents if count > 0],
            "mostReferencedCells": [{"cell": cell, "dependents": count} for cell, count in most_dependents if count > 0]
        }
        
        print(f"Added dependency summary: {total_dependencies} total dependencies across {formula_cells} formula cells")

    def _get_cell_formula(self, cell) -> Optional[str]:
        """Safely get cell formula."""
        try:
            if hasattr(cell, 'value') and isinstance(cell.value, str) and cell.value.startswith('='):
                return cell.value
            return None
        except Exception:
            return None

    def _extract_complete_cell_formatting(self, cell) -> Dict[str, Any]:
        """
        Extract all cell formatting with comprehensive error handling.
        """
        formatting = {}
        
        try:
            # Font properties
            try:
                if cell.font:
                    formatting["font"] = {
                        "name": cell.font.name,
                        "size": cell.font.size,
                        "bold": cell.font.bold,
                        "italic": cell.font.italic,
                        "color": self._get_color_hex(cell.font.color),
                        "underline": cell.font.underline,
                        "strikethrough": cell.font.strikethrough,
                        "vertAlign": cell.font.vertAlign
                    }
            except Exception as e:
                formatting["font"] = {"error": str(e)}
                
            # Fill properties
            try:
                if cell.fill:
                    formatting["fill"] = {
                        "fillType": cell.fill.fill_type,
                        "startColor": self._get_color_hex(cell.fill.start_color),
                        "endColor": self._get_color_hex(cell.fill.end_color),
                        "patternType": cell.fill.patternType
                    }
            except Exception as e:
                formatting["fill"] = {"error": str(e)}
                
            # Number format
            try:
                formatting["numberFormat"] = cell.number_format
            except Exception as e:
                formatting["numberFormat"] = {"error": str(e)}
                
            # Alignment
            try:
                if cell.alignment:
                    formatting["alignment"] = {
                        "horizontal": cell.alignment.horizontal,
                        "vertical": cell.alignment.vertical,
                        "wrapText": cell.alignment.wrap_text,
                        "shrinkToFit": cell.alignment.shrink_to_fit,
                        "indent": cell.alignment.indent,
                        "textRotation": cell.alignment.text_rotation,
                        "readingOrder": cell.alignment.reading_order,
                        "justifyLastLine": cell.alignment.justify_last_line,
                        "relativeIndent": cell.alignment.relative_indent
                    }
            except Exception as e:
                formatting["alignment"] = {"error": str(e)}
                
            # Border properties
            try:
                if cell.border:
                    formatting["borders"] = {
                        "left": self._get_border_info(cell.border.left),
                        "right": self._get_border_info(cell.border.right),
                        "top": self._get_border_info(cell.border.top),
                        "bottom": self._get_border_info(cell.border.bottom),
                        "diagonal": self._get_border_info(cell.border.diagonal),
                        "diagonalUp": cell.border.diagonal_up,
                        "diagonalDown": cell.border.diagonal_down,
                        "outline": cell.border.outline,
                        "start": self._get_border_info(cell.border.start),
                        "end": self._get_border_info(cell.border.end)
                    }
            except Exception as e:
                formatting["borders"] = {"error": str(e)}
                
            # Protection
            try:
                if cell.protection:
                    formatting["protection"] = {
                        "locked": cell.protection.locked,
                        "hidden": cell.protection.hidden
                    }
            except Exception as e:
                formatting["protection"] = {"error": str(e)}
                
            # Comments
            try:
                if cell.comment:
                    formatting["comment"] = {
                        "text": cell.comment.text,
                        "author": cell.comment.author,
                        "width": cell.comment.width,
                        "height": cell.comment.height
                    }
            except Exception as e:
                formatting["comment"] = {"error": str(e)}
                
            # Hyperlink
            try:
                if cell.hyperlink:
                    formatting["hyperlink"] = {
                        "target": cell.hyperlink.target,
                        "tooltip": cell.hyperlink.tooltip,
                        "display": cell.hyperlink.display
                    }
            except Exception as e:
                formatting["hyperlink"] = {"error": str(e)}
                
            # Data type
            try:
                formatting["dataType"] = cell.data_type
            except Exception as e:
                formatting["dataType"] = {"error": str(e)}
                
            # Merged cells
            try:
                merged_ranges = cell.parent.merged_cells.ranges
                is_merged = False
                merge_range = None
                
                for merged_range in merged_ranges:
                    if cell.coordinate in merged_range:
                        is_merged = True
                        merge_range = str(merged_range)
                        break
                        
                formatting["merged"] = {
                    "isMerged": is_merged,
                    "mergeRange": merge_range
                }
            except Exception as e:
                formatting["merged"] = {"error": str(e)}
                
        except Exception as e:
            formatting["error"] = f"Error extracting formatting: {str(e)}"
            print(f"Warning: {formatting['error']}")
            print(traceback.format_exc())
            
        return formatting

    def _get_color_hex(self, color) -> Optional[str]:
        """Safely convert color to hex string."""
        if color is None:
            return None
        
        try:
            # Handle RGB object (newer openpyxl)
            if hasattr(color, 'rgb'):
                if hasattr(color, 'rgb') and color.rgb is not None:
                    # Handle RGB object directly
                    if hasattr(color.rgb, 'rgb'):
                        return f"#{color.rgb.rgb[2:]}"  # Skip alpha channel
                    # Handle string RGB
                    elif isinstance(color.rgb, str):
                        if color.rgb.startswith('FF'):
                            return f"#{color.rgb[2:]}"
                        return f"#{color.rgb}"
                return None
                
            # Handle indexed color
            if hasattr(color, 'indexed') and color.indexed is not None:
                return f"indexed_{color.indexed}"
                
            # Handle theme color
            if hasattr(color, 'theme') and color.theme is not None:
                return f"theme_{color.theme}"
                
            # Handle auto color
            if hasattr(color, 'auto') and color.auto:
                return "auto"
                
            return str(color)
        except Exception as e:
            print(f"Warning: Error converting color to hex: {str(e)}")
            return None

    def _get_border_info(self, border_side) -> Dict[str, Any]:
        """Safely get border information."""
        try:
            if not border_side:
                return {"style": None, "color": None}
                
            return {
                "style": border_side.style,
                "color": self._get_color_hex(border_side.color)
            }
        except Exception as e:
            print(f"Warning: Error getting border info: {str(e)}")
            return {"style": None, "color": None, "error": str(e)}

    def _serialize_value(self, value: Any) -> Any:
        """Safely serialize a cell value."""
        try:
            if value is None:
                return None
            elif isinstance(value, (str, int, float, bool)):
                return value
            elif hasattr(value, 'isoformat'):  # datetime objects
                return value.isoformat()
            else:
                return str(value)
        except Exception as e:
            print(f"Warning: Error serializing value: {str(e)}")
            return None

    def _extract_tables_metadata(self, sheet) -> List[Dict[str, Any]]:
        """Safely extract table metadata."""
        tables = []
        
        try:
            if not hasattr(sheet, 'tables'):
                return tables
                
            for table_name, table in sheet.tables.items():
                try:
                    table_data = {
                        "name": table_name,
                        "displayName": table.displayName,
                        "range": table.ref,
                        "tableStyleInfo": {
                            "name": table.tableStyleInfo.name if table.tableStyleInfo else None,
                            "showFirstColumn": table.tableStyleInfo.showFirstColumn if table.tableStyleInfo else None,
                            "showLastColumn": table.tableStyleInfo.showLastColumn if table.tableStyleInfo else None,
                            "showRowStripes": table.tableStyleInfo.showRowStripes if table.tableStyleInfo else None,
                            "showColumnStripes": table.tableStyleInfo.showColumnStripes if table.tableStyleInfo else None
                        }
                    }
                    
                    # Get column information
                    if hasattr(table, 'tableColumns'):
                        table_data["columns"] = []
                        for col in table.tableColumns:
                            table_data["columns"].append({
                                "name": col.name,
                                "id": col.id
                            })
                    
                    tables.append(table_data)
                    
                except Exception as e:
                    print(f"Warning: Error processing table {table_name}: {str(e)}")
                    continue
                    
        except Exception as e:
            print(f"Warning: Error extracting tables: {str(e)}")
            print(traceback.format_exc())
            
        return tables

    def _extract_named_ranges(self, sheet) -> List[Dict[str, Any]]:
        """Safely extract named ranges."""
        named_ranges = []
        
        try:
            if not hasattr(self.workbook, 'defined_names') or not self.workbook.defined_names:
                return named_ranges
                
            # Handle both old and new openpyxl versions
            if hasattr(self.workbook.defined_names, 'definedName'):
                # Old openpyxl version
                names = self.workbook.defined_names.definedName
            else:
                # New openpyxl version - defined_names is already a dict-like object
                names = self.workbook.defined_names.values()
                
            for defined_name in names:
                try:
                    # Get the name and value, handling different openpyxl versions
                    name = defined_name.name if hasattr(defined_name, 'name') else defined_name
                    value = defined_name.value if hasattr(defined_name, 'value') else str(defined_name)
                    
                    if sheet.title in str(value):
                        named_range = {
                            "name": name,
                            "value": str(value)
                        }
                        
                        # Add optional fields if they exist
                        if hasattr(defined_name, 'localSheetId'):
                            named_range["localSheetId"] = defined_name.localSheetId
                        if hasattr(defined_name, 'hidden'):
                            named_range["hidden"] = defined_name.hidden
                            
                        named_ranges.append(named_range)
                        
                except Exception as e:
                    print(f"Warning: Error processing named range: {str(e)}")
                    continue
                    
        except Exception as e:
            print(f"Warning: Error extracting named ranges: {str(e)}")
            print(traceback.format_exc())
            
        return named_ranges

    def _get_theme_colors(self) -> Dict[str, str]:
        """Get theme colors with fallback to defaults."""
        try:
            # Try to get actual theme colors if available
            if hasattr(self.workbook, 'theme') and hasattr(self.workbook.theme, 'theme_elements'):
                # This is a simplified example - actual implementation would need to
                # extract colors from the theme XML
                pass
        except Exception as e:
            print(f"Warning: Error getting theme colors: {str(e)}")
        
        # Default theme colors (Office theme) as fallback
        return {
            "background1": "#FFFFFF",
            "background2": "#F2F2F2", 
            "text1": "#000000",
            "text2": "#666666",
            "accent1": "#4472C4",
            "accent2": "#ED7D31",
            "accent3": "#A5A5A5",
            "accent4": "#FFC000",
            "accent5": "#5B9BD5",
            "accent6": "#70AD47",
            "hyperlink": "#0563C1",
            "followedHyperlink": "#954F72"
        }

    def extract_to_json_str(
        self,
        workbook_path: Optional[str] = None,
        output_path: Optional[str] = None,
        max_rows_per_sheet: int = 100,
        max_cols_per_sheet: int = 50,
        include_dependencies: bool = True,
        **kwargs
    ) -> str:
        """
        Extract metadata and return as JSON string with comprehensive error handling and dependencies.
        """
        try:
            # Extract metadata
            metadata, display_values = self.extract_workbook_metadata(
                workbook_path=workbook_path,
                max_rows_per_sheet=max_rows_per_sheet,
                max_cols_per_sheet=max_cols_per_sheet,
                include_dependencies=include_dependencies,
                **kwargs
            )
            
            # Prepare result
            result = {
                "metadata": metadata,
                "displayValues": display_values,
                "status": "success",
                "timestamp": datetime.now().isoformat()
            }
            
            # Convert to JSON
            json_str = json.dumps(result, indent=2, ensure_ascii=False)
            
            # Save to file if output path is provided
            if output_path:
                try:
                    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
                    with open(output_path, 'w', encoding='utf-8') as f:
                        f.write(json_str)
                    print(f"Metadata successfully saved to: {output_path}")
                except Exception as e:
                    raise IOError(f"Failed to write output file: {str(e)}")
                    
            return json_str
            
        except Exception as e:
            # Prepare error response
            error_msg = f"Failed to extract metadata to JSON: {str(e)}"
            print(error_msg)
            print(traceback.format_exc())
            
            error_result = {
                "metadata": None,
                "displayValues": None,
                "status": "error",
                "error": error_msg,
                "timestamp": datetime.now().isoformat()
            }
            
            return json.dumps(error_result, indent=2)

    def extract_workbook_metadata_chunks(
        self,
        workbook_path: Optional[str] = None,
        rows_per_chunk: int = 10,
        max_cols_per_sheet: int = 50,
        include_dependencies: bool = True,
        include_empty_chunks: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Extract metadata in chunks of N rows, returning an array of metadata objects.
        
        Args:
            workbook_path: Path to the Excel file
            rows_per_chunk: Number of rows per chunk (default 10)
            max_cols_per_sheet: Maximum columns to extract per sheet
            include_dependencies: Whether to include dependency analysis
            include_empty_chunks: Whether to include chunks with no data
            
        Returns:
            List of metadata dictionaries, one per chunk
        """
        try:
            if workbook_path or not self.workbook:
                self.open_workbook(workbook_path)
                
            if not self.workbook:
                raise RuntimeError("Workbook is not open")
            
            chunks = []
            all_cells_metadata = {}  # For dependency analysis across all chunks
            chunk_to_cells_map = {}  # Map chunk index to its cells for dependency updates
            
            # Get workbook info
            workbook_name = os.path.basename(self.workbook_path) if self.workbook_path else "Unknown"
            
            # Process each sheet
            for sheet in self.workbook.worksheets:
                try:
                    sheet_name = sheet.title
                    
                    # Get actual dimensions
                    actual_row_count = min(sheet.max_row or 0, 1048576)
                    actual_col_count = min(sheet.max_column or 0, 16384)
                    
                    if actual_row_count == 0 or actual_col_count == 0:
                        continue
                    
                    # Extract columns to process
                    cols_to_extract = min(actual_col_count, max_cols_per_sheet)
                    
                    # Process sheet in chunks
                    for chunk_start_row in range(1, actual_row_count + 1, rows_per_chunk):
                        chunk_end_row = min(chunk_start_row + rows_per_chunk - 1, actual_row_count)
                        
                        # Extract chunk metadata
                        chunk_metadata = {
                            "chunkId": f"{workbook_name}_{sheet_name}_rows_{chunk_start_row}_{chunk_end_row}",
                            "workbookName": workbook_name,
                            "workbookPath": self.workbook_path,
                            "sheetName": sheet_name,
                            "startRow": chunk_start_row,
                            "endRow": chunk_end_row,
                            "rowCount": chunk_end_row - chunk_start_row + 1,
                            "columnCount": cols_to_extract,
                            "extractedAt": datetime.now().isoformat(),
                            "cellData": [],
                            "chunkIndex": len(chunks),
                            "includeDependencies": include_dependencies
                        }
                        
                        # Extract cell data for this chunk
                        chunk_cells, chunk_cells_dict = self._extract_chunk_cell_data(
                            sheet,
                            chunk_start_row,
                            chunk_end_row,
                            cols_to_extract
                        )
                        
                        # Skip empty chunks if requested
                        if not include_empty_chunks and not any(
                            any(cell.get('value') is not None or cell.get('formula') 
                                for cell in row) 
                            for row in chunk_cells
                        ):
                            continue
                        
                        chunk_metadata["cellData"] = chunk_cells
                        
                        # Store cells for dependency analysis
                        all_cells_metadata.update(chunk_cells_dict)
                        chunk_to_cells_map[len(chunks)] = list(chunk_cells_dict.keys())
                        
                        # Extract tables that intersect with this chunk
                        chunk_metadata["tables"] = self._extract_tables_in_range(
                            sheet,
                            chunk_start_row,
                            chunk_end_row,
                            1,
                            cols_to_extract
                        )
                        
                        chunks.append(chunk_metadata)
                        
                except Exception as e:
                    error_msg = f"Error processing sheet '{sheet.title}': {str(e)}"
                    print(f"Warning: {error_msg}")
                    print(traceback.format_exc())
                    
                    # Add error chunk
                    chunks.append({
                        "workbookName": workbook_name,
                        "workbookPath": self.workbook_path,
                        "sheetName": sheet.title,
                        "error": error_msg,
                        "chunkIndex": len(chunks)
                    })
            
            # Build dependencies if requested
            if include_dependencies and all_cells_metadata:
                print(f"Building dependencies for {len(chunks)} chunks...")
                try:
                    dependency_map, dependent_map = self.dependency_extractor.build_dependency_maps(all_cells_metadata)
                    
                    # Update each chunk with dependency information
                    for chunk_idx, chunk_cell_addresses in chunk_to_cells_map.items():
                        self._update_chunk_with_dependencies(
                            chunks[chunk_idx],
                            chunk_cell_addresses,
                            dependency_map,
                            dependent_map
                        )
                        
                except Exception as e:
                    print(f"Warning: Error building dependencies: {str(e)}")
            
            return chunks
            
        except Exception as e:
            error_msg = f"Failed to extract chunk metadata: {str(e)}"
            print(error_msg)
            print(traceback.format_exc())
            raise RuntimeError(error_msg) from e

    def _extract_chunk_cell_data(
        self,
        sheet,
        start_row: int,
        end_row: int,
        col_count: int
    ) -> Tuple[List[List[Dict[str, Any]]], Dict[str, Any]]:
        """
        Extract cell data for a specific chunk range.
        """
        cell_data = []
        cell_dict = {}  # For dependency analysis
        
        try:
            for row_idx in range(start_row, end_row + 1):
                row_data = []
                
                for col_idx in range(1, col_count + 1):
                    try:
                        cell = sheet.cell(row=row_idx, column=col_idx)
                        # Reuse existing method
                        cell_metadata = self._extract_complete_cell_metadata(
                            cell, row_idx, col_idx, sheet.title
                        )
                        row_data.append(cell_metadata)
                        
                        # Add to dictionary for dependency analysis if has content
                        if cell_metadata.get('value') is not None or cell_metadata.get('formula'):
                            full_address = f"{sheet.title}!{cell_metadata['address']}"
                            cell_dict[full_address] = cell_metadata
                            
                    except Exception as e:
                        print(f"Warning: Error processing cell ({row_idx},{col_idx}): {str(e)}")
                        row_data.append({
                            "row": row_idx,
                            "column": col_idx,
                            "address": f"{get_column_letter(col_idx)}{row_idx}",
                            "error": str(e)
                        })
                
                cell_data.append(row_data)
                
        except Exception as e:
            print(f"Error extracting chunk cell data: {str(e)}")
            print(traceback.format_exc())
            raise
            
        return cell_data, cell_dict

    def _extract_tables_in_range(
        self,
        sheet,
        start_row: int,
        end_row: int,
        start_col: int,
        end_col: int
    ) -> List[Dict[str, Any]]:
        """
        Extract tables that intersect with the given range.
        """
        tables = []
        
        try:
            if not hasattr(sheet, 'tables'):
                return tables
                
            for table_name, table in sheet.tables.items():
                try:
                    # Parse table range
                    table_range = table.ref
                    if ':' in table_range:
                        start_cell, end_cell = table_range.split(':')
                        
                        # Extract row and column from cell addresses
                        table_start_col = self.dependency_extractor.parse_cell_address(start_cell)[0]
                        table_start_row = self.dependency_extractor.parse_cell_address(start_cell)[1]
                        table_end_col = self.dependency_extractor.parse_cell_address(end_cell)[0]
                        table_end_row = self.dependency_extractor.parse_cell_address(end_cell)[1]
                        
                        # Check if table intersects with chunk range
                        if (table_start_row <= end_row and table_end_row >= start_row and
                            table_start_col <= end_col and table_end_col >= start_col):
                            
                            # Add table metadata (reuse existing method logic)
                            table_data = {
                                "name": table_name,
                                "displayName": table.displayName,
                                "range": table.ref,
                                "intersectsChunk": True,
                                "tableStyleInfo": {
                                    "name": table.tableStyleInfo.name if table.tableStyleInfo else None,
                                    "showFirstColumn": table.tableStyleInfo.showFirstColumn if table.tableStyleInfo else None,
                                    "showLastColumn": table.tableStyleInfo.showLastColumn if table.tableStyleInfo else None,
                                    "showRowStripes": table.tableStyleInfo.showRowStripes if table.tableStyleInfo else None,
                                    "showColumnStripes": table.tableStyleInfo.showColumnStripes if table.tableStyleInfo else None
                                }
                            }
                            
                            # Get column information if available
                            if hasattr(table, 'tableColumns'):
                                table_data["columns"] = []
                                for col in table.tableColumns:
                                    table_data["columns"].append({
                                        "name": col.name,
                                        "id": col.id
                                    })
                            
                            tables.append(table_data)
                            
                except Exception as e:
                    print(f"Warning: Error processing table {table_name} for chunk: {str(e)}")
                    continue
                    
        except Exception as e:
            print(f"Warning: Error extracting tables for chunk: {str(e)}")
            
        return tables

    def _update_chunk_with_dependencies(
        self,
        chunk_metadata: Dict[str, Any],
        chunk_cell_addresses: List[str],
        dependency_map: Dict[str, set],
        dependent_map: Dict[str, set]
    ):
        """
        Update chunk cells with dependency information.
        """
        # Update cells in the chunk
        for row_data in chunk_metadata["cellData"]:
            for cell_metadata in row_data:
                if "address" in cell_metadata:
                    full_address = f"{chunk_metadata['sheetName']}!{cell_metadata['address']}"
                    
                    # Get dependency information
                    precedents = dependency_map.get(full_address, set())
                    dependents = dependent_map.get(full_address, set())
                    
                    # Update cell metadata (reuse existing logic)
                    cell_metadata.update({
                        "directPrecedents": list(precedents),
                        "directDependents": list(dependents),
                        "precedentCount": len(precedents),
                        "dependentCount": len(dependents),
                        "totalConnections": len(precedents) + len(dependents)
                    })
        
        # Add chunk-level dependency summary
        chunk_precedents = set()
        chunk_dependents = set()
        internal_dependencies = 0
        external_dependencies = 0
        
        for cell_addr in chunk_cell_addresses:
            # Collect all dependencies for this chunk
            cell_precedents = dependency_map.get(cell_addr, set())
            cell_dependents = dependent_map.get(cell_addr, set())
            
            chunk_precedents.update(cell_precedents)
            chunk_dependents.update(cell_dependents)
            
            # Count internal vs external dependencies
            for prec in cell_precedents:
                if prec in chunk_cell_addresses:
                    internal_dependencies += 1
                else:
                    external_dependencies += 1
        
        # Add dependency summary to chunk
        chunk_metadata["dependencySummary"] = {
            "totalPrecedents": len(chunk_precedents),
            "totalDependents": len(chunk_dependents),
            "internalDependencies": internal_dependencies,
            "externalDependencies": external_dependencies,
            "externalPrecedents": list(chunk_precedents - set(chunk_cell_addresses))[:10],  # Top 10
            "externalDependents": list(chunk_dependents - set(chunk_cell_addresses))[:10]   # Top 10
        }