import xlwings as xw
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import os

class XlwingsMetadataExtractor:
    """
    Python class for extracting comprehensive cell-based metadata from Excel workbooks using xlwings.
    Each cell contains all its data and formatting information in a single object.
    """
    
    def __init__(self, workbook_path: Optional[str] = None, app_visible: bool = False):
        """
        Initialize the metadata extractor.
        
        Args:
            workbook_path: Path to the Excel file (optional, can be set later)
            app_visible: Whether to make Excel application visible
        """
        self.workbook_path = workbook_path
        self.app_visible = app_visible
        self.app = None
        self.workbook = None
        
    def __enter__(self):
        """Context manager entry"""
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup resources"""
        self.close()
        
    def open_workbook(self, workbook_path: Optional[str] = None) -> None:
        """
        Open the Excel workbook.
        
        Args:
            workbook_path: Path to the Excel file
        """
        if workbook_path:
            self.workbook_path = workbook_path
            
        if not self.workbook_path:
            raise ValueError("No workbook path specified")
            
        if not os.path.exists(self.workbook_path):
            raise FileNotFoundError(f"Workbook not found: {self.workbook_path}")
            
        try:
            # Create or get Excel application
            self.app = xw.App(visible=self.app_visible)
            
            # Open the workbook
            self.workbook = self.app.books.open(self.workbook_path)
            
        except Exception as e:
            if self.app:
                self.app.quit()
            raise Exception(f"Failed to open workbook: {str(e)}")
            
    def close(self) -> None:
        """Close the workbook and Excel application"""
        try:
            if self.workbook:
                self.workbook.close()
                self.workbook = None
                
            if self.app:
                self.app.quit()
                self.app = None
        except Exception as e:
            print(f"Warning: Error during cleanup: {str(e)}")
            
    def extract_workbook_metadata(self, workbook_path: Optional[str] = None, max_rows_per_sheet: int = 100, max_cols_per_sheet: int = 50) -> Dict[str, Any]:
        """
        Extract comprehensive metadata from the Excel workbook with cell-based structure.
        
        Args:
            workbook_path: Path to the Excel file
            max_rows_per_sheet: Maximum number of rows to extract per sheet
            max_cols_per_sheet: Maximum number of columns to extract per sheet
            
        Returns:
            Dictionary containing complete workbook metadata
        """
        if workbook_path or not self.workbook:
            self.open_workbook(workbook_path)
            
        try:
            # Get basic workbook info
            workbook_metadata = {
                "extractedAt": datetime.now().isoformat(),
                "workbookPath": self.workbook_path,
                "workbookName": self.workbook.name,
                "activeSheet": self.workbook.sheets.active.name,
                "totalSheets": len(self.workbook.sheets),
                "sheetNames": [sheet.name for sheet in self.workbook.sheets],
                "themeColors": self._get_theme_colors(),
                "sheets": []
            }
            
            # Extract metadata for each sheet
            for sheet in self.workbook.sheets:
                sheet_metadata = self._extract_sheet_metadata(sheet, max_rows_per_sheet, max_cols_per_sheet)
                workbook_metadata["sheets"].append(sheet_metadata)
                
            return workbook_metadata
            
        except Exception as e:
            raise Exception(f"Failed to extract workbook metadata: {str(e)}")
            
    def _extract_sheet_metadata(self, sheet: xw.Sheet, max_rows: int, max_cols: int) -> Dict[str, Any]:
        """
        Extract comprehensive metadata from a single sheet with cell-based structure.
        
        Args:
            sheet: xlwings Sheet object
            max_rows: Maximum number of rows to extract
            max_cols: Maximum number of columns to extract
            
        Returns:
            Dictionary containing sheet metadata
        """
        try:
            # Get used range
            used_range = sheet.used_range
            
            if not used_range:
                return {
                    "name": sheet.name,
                    "isEmpty": True,
                    "rowCount": 0,
                    "columnCount": 0,
                    "cellData": [],
                    "tables": [],
                    "charts": [],
                    "namedRanges": []
                }
                
            # Get actual dimensions
            actual_row_count = used_range.shape[0]
            actual_col_count = used_range.shape[1]
            
            # Determine extraction bounds
            extract_row_count = min(actual_row_count, max_rows)
            extract_col_count = min(actual_col_count, max_cols)
            
            # Extract cell data in the required format
            cell_data = self._extract_cell_data(sheet, extract_row_count, extract_col_count)
            
            # Extract other sheet elements
            tables = self._extract_tables_metadata(sheet)
            charts = self._extract_charts_metadata(sheet)
            named_ranges = self._extract_named_ranges(sheet)
            
            return {
                "name": sheet.name,
                "isEmpty": False,
                "rowCount": actual_row_count,
                "columnCount": actual_col_count,
                "extractedRowCount": extract_row_count,
                "extractedColumnCount": extract_col_count,
                "cellData": cell_data,
                "tables": tables,
                "charts": charts,
                "namedRanges": named_ranges
            }
            
        except Exception as e:
            print(f"Warning: Error extracting metadata for sheet '{sheet.name}': {str(e)}")
            return {
                "name": sheet.name,
                "error": str(e),
                "isEmpty": True,
                "rowCount": 0,
                "columnCount": 0,
                "cellData": [],
                "tables": [],
                "charts": [],
                "namedRanges": []
            }
            
    def _extract_cell_data(self, sheet: xw.Sheet, row_count: int, col_count: int) -> List[List[Dict[str, Any]]]:
        """
        Extract comprehensive cell data including values, formulas, and all formatting.
        
        Args:
            sheet: xlwings Sheet object
            row_count: Number of rows to extract
            col_count: Number of columns to extract
            
        Returns:
            2D array of cell objects with complete metadata
        """
        try:
            cell_data = []
            
            # Extract data row by row
            for row_idx in range(row_count):
                row_data = []
                
                for col_idx in range(col_count):
                    # Get cell (1-based indexing for Excel)
                    cell = sheet.range(row_idx + 1, col_idx + 1)
                    
                    # Extract complete cell metadata
                    cell_metadata = self._extract_complete_cell_metadata(cell, row_idx + 1, col_idx + 1)
                    row_data.append(cell_metadata)
                    
                cell_data.append(row_data)
                
            return cell_data
            
        except Exception as e:
            print(f"Warning: Error extracting cell data: {str(e)}")
            return []

    def _extract_display_values(self, workbook_path: str, metadata: Dict[str, Any]) -> Dict[str, str]:
        """
        Use xlwings to extract only the display values (what user sees in Excel).
        
        Args:
            workbook_path: Path to Excel file
            metadata: Metadata from openpyxl extraction
            
        Returns:
            Dictionary mapping cell keys to display values
        """
        display_values = {}
        
        try:            
            # Open Excel with xlwings (visible=False for speed)
            app = xw.App(visible=False)
            wb = app.books.open(workbook_path)
            
            print("Extracting display values with xlwings...")
            
            for sheet_data in metadata.get("sheets", []):
                if sheet_data.get("isEmpty", True):
                    continue
                    
                sheet_name = sheet_data.get("name", "")
                
                try:
                    ws = wb.sheets[sheet_name]
                    
                    # Get display values for all significant cells
                    for row_data in sheet_data.get("cellData", []):
                        for cell in row_data:
                            if self._is_significant_cell(cell):
                                row = cell.get("row")
                                col = cell.get("column")
                                
                                try:
                                    # Get the displayed text (formatted value)
                                    cell_range = ws.range(row, col)
                                    display_text = cell_range.api.Text
                                    
                                    # Store with unique key
                                    cell_key = f"{sheet_name}_{row}_{col}"
                                    display_values[cell_key] = str(display_text) if display_text else ""
                                    
                                except Exception as e:
                                    print(f"Warning: Could not get display value for {sheet_name} R{row}C{col}: {str(e)}")
                                    continue
                                    
                except Exception as e:
                    print(f"Warning: Error processing sheet {sheet_name}: {str(e)}")
                    continue
            
            # Close xlwings
            wb.close()
            app.quit()
            
            print(f"Extracted {len(display_values)} display values")
            return display_values
            
        except Exception as e:
            print(f"Warning: Could not extract display values with xlwings: {str(e)}")
            return {}
            
    def _extract_complete_cell_metadata(self, cell: xw.Range, row: int, col: int) -> Dict[str, Any]:
        """
        Extract complete metadata for a single cell including all possible properties.
        
        Args:
            cell: xlwings Range object representing the cell
            row: 1-based row number
            col: 1-based column number
            
        Returns:
            Dictionary containing all cell metadata
        """
        try:
            cell_metadata = {
                "row": row,
                "column": col,
                "address": cell.address,
                "value": self._serialize_value(cell.value),
                "formula": self._get_cell_formula(cell),
                "formatting": self._extract_complete_cell_formatting(cell)
            }
            
            return cell_metadata
            
        except Exception as e:
            print(f"Warning: Error extracting cell metadata for {row},{col}: {str(e)}")
            return {
                "row": row,
                "column": col,
                "address": f"${chr(64 + col)}${row}",
                "value": None,
                "formula": None,
                "formatting": {},
                "error": str(e)
            }
            
    def _get_cell_formula(self, cell: xw.Range) -> Optional[str]:
        """Get the formula from a cell"""
        try:
            formula = cell.formula
            if formula and formula.startswith('='):
                return formula
            elif formula:
                return str(formula)
            return None
        except:
            return None
            
    def _extract_complete_cell_formatting(self, cell: xw.Range) -> Dict[str, Any]:
        """
        Extract all possible formatting properties from a cell.
        
        Args:
            cell: xlwings Range object
            
        Returns:
            Dictionary containing all formatting properties
        """
        formatting = {}
        
        try:
            # Font properties
            try:
                formatting["font"] = {
                    "name": cell.font.name,
                    "size": cell.font.size,
                    "bold": cell.font.bold,
                    "italic": cell.font.italic,
                    "color": self._color_to_hex(cell.font.color),
                    "underline": self._get_underline_style(cell),
                    "strikethrough": self._get_strikethrough(cell),
                    "subscript": self._get_subscript(cell),
                    "superscript": self._get_superscript(cell)
                }
            except Exception as e:
                formatting["font"] = {"error": str(e)}
                
            # Fill/Background properties
            try:
                formatting["fill"] = {
                    "color": self._color_to_hex(cell.color),
                    "pattern": self._get_fill_pattern(cell),
                    "patternColor": self._get_pattern_color(cell)
                }
            except Exception as e:
                formatting["fill"] = {"error": str(e)}
                
            # Number format
            try:
                formatting["numberFormat"] = cell.number_format
            except Exception as e:
                formatting["numberFormat"] = {"error": str(e)}
                
            # Alignment properties
            try:
                formatting["alignment"] = {
                    "horizontal": self._get_horizontal_alignment(cell),
                    "vertical": self._get_vertical_alignment(cell),
                    "wrapText": self._get_wrap_text(cell),
                    "shrinkToFit": self._get_shrink_to_fit(cell),
                    "indent": self._get_indent_level(cell),
                    "textRotation": self._get_text_rotation(cell),
                    "readingOrder": self._get_reading_order(cell)
                }
            except Exception as e:
                formatting["alignment"] = {"error": str(e)}
                
            # Border properties
            try:
                formatting["borders"] = {
                    "left": self._get_border_info(cell, "left"),
                    "right": self._get_border_info(cell, "right"),
                    "top": self._get_border_info(cell, "top"),
                    "bottom": self._get_border_info(cell, "bottom"),
                    "diagonal": self._get_border_info(cell, "diagonal"),
                    "diagonalUp": self._get_diagonal_up(cell),
                    "diagonalDown": self._get_diagonal_down(cell)
                }
            except Exception as e:
                formatting["borders"] = {"error": str(e)}
                
            # Protection properties
            try:
                formatting["protection"] = {
                    "locked": self._get_locked_status(cell),
                    "formulaHidden": self._get_formula_hidden(cell)
                }
            except Exception as e:
                formatting["protection"] = {"error": str(e)}
                
            # Conditional formatting
            try:
                formatting["conditionalFormatting"] = self._get_conditional_formatting(cell)
            except Exception as e:
                formatting["conditionalFormatting"] = {"error": str(e)}
                
            # Data validation
            try:
                formatting["dataValidation"] = self._get_data_validation(cell)
            except Exception as e:
                formatting["dataValidation"] = {"error": str(e)}
                
            # Comments/Notes
            try:
                formatting["comment"] = self._get_cell_comment(cell)
            except Exception as e:
                formatting["comment"] = {"error": str(e)}
                
            # Merged cell information
            try:
                formatting["merged"] = {
                    "isMerged": self._is_merged_cell(cell),
                    "mergeArea": self._get_merge_area(cell)
                }
            except Exception as e:
                formatting["merged"] = {"error": str(e)}
                
        except Exception as e:
            formatting["extractionError"] = str(e)
            
        return formatting
        
    # Helper methods for formatting extraction
    def _color_to_hex(self, color: Any) -> Optional[str]:
        """Convert xlwings color to hex string"""
        try:
            if color is None:
                return None
            if isinstance(color, tuple) and len(color) == 3:
                return f"#{color[0]:02X}{color[1]:02X}{color[2]:02X}"
            elif isinstance(color, int):
                # Convert BGR integer to RGB hex
                blue = (color >> 16) & 0xFF
                green = (color >> 8) & 0xFF
                red = color & 0xFF
                return f"#{red:02X}{green:02X}{blue:02X}"
            return str(color)
        except:
            return None
            
    def _get_underline_style(self, cell: xw.Range) -> str:
        """Get underline style"""
        try:
            return str(cell.api.Font.Underline)
        except:
            return "none"
            
    def _get_strikethrough(self, cell: xw.Range) -> bool:
        """Get strikethrough status"""
        try:
            return bool(cell.api.Font.Strikethrough)
        except:
            return False
            
    def _get_subscript(self, cell: xw.Range) -> bool:
        """Get subscript status"""
        try:
            return bool(cell.api.Font.Subscript)
        except:
            return False
            
    def _get_superscript(self, cell: xw.Range) -> bool:
        """Get superscript status"""
        try:
            return bool(cell.api.Font.Superscript)
        except:
            return False
            
    def _get_fill_pattern(self, cell: xw.Range) -> str:
        """Get fill pattern"""
        try:
            return str(cell.api.Interior.Pattern)
        except:
            return "solid"
            
    def _get_pattern_color(self, cell: xw.Range) -> Optional[str]:
        """Get pattern color"""
        try:
            return self._color_to_hex(cell.api.Interior.PatternColor)
        except:
            return None
            
    def _get_horizontal_alignment(self, cell: xw.Range) -> str:
        """Get horizontal alignment"""
        try:
            alignment_map = {
                -4108: "center",
                -4131: "left", 
                -4152: "right",
                -4130: "justify",
                1: "general",
                7: "fill",
                6: "centerAcrossSelection",
                5: "distributed"
            }
            return alignment_map.get(cell.api.HorizontalAlignment, "general")
        except:
            return "general"
            
    def _get_vertical_alignment(self, cell: xw.Range) -> str:
        """Get vertical alignment"""
        try:
            alignment_map = {
                -4108: "center",
                -4160: "top",
                -4107: "bottom",
                -4130: "justify",
                -4117: "distributed"
            }
            return alignment_map.get(cell.api.VerticalAlignment, "bottom")
        except:
            return "bottom"
            
    def _get_wrap_text(self, cell: xw.Range) -> bool:
        """Get wrap text status"""
        try:
            return bool(cell.api.WrapText)
        except:
            return False
            
    def _get_shrink_to_fit(self, cell: xw.Range) -> bool:
        """Get shrink to fit status"""
        try:
            return bool(cell.api.ShrinkToFit)
        except:
            return False
            
    def _get_indent_level(self, cell: xw.Range) -> int:
        """Get indent level"""
        try:
            return int(cell.api.IndentLevel)
        except:
            return 0
            
    def _get_text_rotation(self, cell: xw.Range) -> int:
        """Get text rotation angle"""
        try:
            return int(cell.api.Orientation)
        except:
            return 0
            
    def _get_reading_order(self, cell: xw.Range) -> str:
        """Get reading order"""
        try:
            order_map = {
                -5002: "context",
                -5003: "leftToRight",
                -5004: "rightToLeft"
            }
            return order_map.get(cell.api.ReadingOrder, "context")
        except:
            return "context"
            
    def _get_border_info(self, cell: xw.Range, side: str) -> Dict[str, Any]:
        """Get border information for a specific side"""
        try:
            border_map = {
                "left": 7,
                "right": 10,
                "top": 8,
                "bottom": 9,
                "diagonal": 5
            }
            
            if side not in border_map:
                return {"style": "none", "color": None, "weight": 0}
                
            border = cell.api.Borders(border_map[side])
            
            style_map = {
                1: "continuous",
                2: "dash",
                3: "dashDot",
                4: "dashDotDot",
                5: "dot",
                13: "slantDashDot",
                -4119: "double",
                -4142: "none"
            }
            
            return {
                "style": style_map.get(border.LineStyle, "none"),
                "color": self._color_to_hex(border.Color),
                "weight": border.Weight if hasattr(border, 'Weight') else 0
            }
        except:
            return {"style": "none", "color": None, "weight": 0}
            
    def _get_diagonal_up(self, cell: xw.Range) -> bool:
        """Get diagonal up border status"""
        try:
            return bool(cell.api.Borders.Item(6).LineStyle != -4142)
        except:
            return False
            
    def _get_diagonal_down(self, cell: xw.Range) -> bool:
        """Get diagonal down border status"""
        try:
            return bool(cell.api.Borders.Item(5).LineStyle != -4142)
        except:
            return False
            
    def _get_locked_status(self, cell: xw.Range) -> bool:
        """Get cell locked status"""
        try:
            return bool(cell.api.Locked)
        except:
            return True
            
    def _get_formula_hidden(self, cell: xw.Range) -> bool:
        """Get formula hidden status"""
        try:
            return bool(cell.api.FormulaHidden)
        except:
            return False
            
    def _get_conditional_formatting(self, cell: xw.Range) -> List[Dict[str, Any]]:
        """Get conditional formatting rules"""
        try:
            cf_rules = []
            for cf in cell.api.FormatConditions:
                rule = {
                    "type": str(cf.Type),
                    "formula1": str(cf.Formula1) if hasattr(cf, 'Formula1') else None,
                    "formula2": str(cf.Formula2) if hasattr(cf, 'Formula2') else None,
                    "operator": str(cf.Operator) if hasattr(cf, 'Operator') else None
                }
                cf_rules.append(rule)
            return cf_rules
        except:
            return []
            
    def _get_data_validation(self, cell: xw.Range) -> Dict[str, Any]:
        """Get data validation information"""
        try:
            validation = cell.api.Validation
            return {
                "type": str(validation.Type),
                "alertStyle": str(validation.AlertStyle),
                "operator": str(validation.Operator),
                "formula1": str(validation.Formula1) if validation.Formula1 else None,
                "formula2": str(validation.Formula2) if validation.Formula2 else None,
                "inputTitle": str(validation.InputTitle) if validation.InputTitle else None,
                "inputMessage": str(validation.InputMessage) if validation.InputMessage else None,
                "errorTitle": str(validation.ErrorTitle) if validation.ErrorTitle else None,
                "errorMessage": str(validation.ErrorMessage) if validation.ErrorMessage else None
            }
        except:
            return {}
            
    def _get_cell_comment(self, cell: xw.Range) -> Optional[Dict[str, Any]]:
        """Get cell comment/note"""
        try:
            if cell.api.Comment:
                return {
                    "text": str(cell.api.Comment.Text()),
                    "author": str(cell.api.Comment.Author) if hasattr(cell.api.Comment, 'Author') else None,
                    "visible": bool(cell.api.Comment.Visible)
                }
            return None
        except:
            return None
            
    def _is_merged_cell(self, cell: xw.Range) -> bool:
        """Check if cell is part of a merged range"""
        try:
            return bool(cell.api.MergeCells)
        except:
            return False
            
    def _get_merge_area(self, cell: xw.Range) -> Optional[str]:
        """Get the address of the merged area"""
        try:
            if cell.api.MergeCells:
                return str(cell.api.MergeArea.Address)
            return None
        except:
            return None
            
    def _serialize_value(self, value: Any) -> Any:
        """Serialize a cell value to JSON-compatible format"""
        if value is None:
            return None
        elif isinstance(value, (str, int, float, bool)):
            return value
        elif hasattr(value, 'isoformat'):  # datetime objects
            return value.isoformat()
        else:
            return str(value)
            
    def _extract_tables_metadata(self, sheet: xw.Sheet) -> List[Dict[str, Any]]:
        """Extract metadata about tables in the sheet"""
        try:
            tables = []
            
            # Get tables using the API
            for table in sheet.api.ListObjects:
                try:
                    table_data = {
                        "name": table.Name,
                        "range": table.Range.Address,
                        "hasHeaders": table.HeaderRowRange is not None,
                        "headers": [],
                        "totalRows": table.Range.Rows.Count,
                        "totalColumns": table.Range.Columns.Count,
                        "showTotals": bool(table.ShowTotals) if hasattr(table, 'ShowTotals') else False
                    }
                    
                    # Get headers if they exist
                    if table.HeaderRowRange:
                        header_range = sheet.range(table.HeaderRowRange.Address)
                        headers = header_range.value
                        if isinstance(headers, list):
                            table_data["headers"] = [str(h) if h else "" for h in headers]
                        else:
                            table_data["headers"] = [str(headers) if headers else ""]
                            
                    tables.append(table_data)
                    
                except Exception as e:
                    print(f"Warning: Error processing table: {str(e)}")
                    continue
                    
            return tables
            
        except Exception as e:
            print(f"Warning: Error extracting tables metadata: {str(e)}")
            return []
        
    def _extract_charts_metadata(self, sheet: xw.Sheet) -> List[Dict[str, Any]]:
        """Extract metadata about charts in the sheet"""
        try:
            charts = []
            
            # Get charts using the API
            chart_objects = sheet.api.ChartObjects()
            
            # Check if there are any charts
            if chart_objects.Count == 0:
                return charts
                
            # Iterate through charts by index
            for i in range(1, chart_objects.Count + 1):
                try:
                    chart = chart_objects.Item(i)
                    chart_data = {
                        "name": chart.Name,
                        "chartType": str(chart.Chart.ChartType),
                        "position": {
                            "left": chart.Left,
                            "top": chart.Top,
                            "width": chart.Width,
                            "height": chart.Height
                        },
                        "hasTitle": bool(chart.Chart.HasTitle),
                        "hasLegend": bool(chart.Chart.HasLegend)
                    }
                    
                    # Try to get chart title
                    try:
                        if chart.Chart.HasTitle:
                            chart_data["title"] = chart.Chart.ChartTitle.Text
                    except:
                        pass
                        
                    # Try to get data source
                    try:
                        if chart.Chart.SeriesCollection().Count > 0:
                            chart_data["sourceData"] = chart.Chart.SeriesCollection(1).Formula
                    except:
                        pass
                        
                    charts.append(chart_data)
                    
                except Exception as e:
                    print(f"Warning: Error processing chart {i}: {str(e)}")
                    continue
                    
            return charts
            
        except Exception as e:
            print(f"Warning: Error extracting charts metadata: {str(e)}")
            return []

            
    def _extract_named_ranges(self, sheet: xw.Sheet) -> List[Dict[str, Any]]:
        """Extract named ranges that reference this sheet"""
        try:
            named_ranges = []
            
            # Get named ranges from workbook
            for name in self.workbook.api.Names:
                try:
                    # Check if the named range refers to this sheet
                    refers_to = name.RefersTo
                    if sheet.name in refers_to:
                        named_ranges.append({
                            "name": name.Name,
                            "refersTo": refers_to,
                            "scope": "Workbook" if name.Parent == self.workbook.api else "Worksheet",
                            "visible": bool(name.Visible) if hasattr(name, 'Visible') else True
                        })
                except Exception as e:
                    print(f"Warning: Error processing named range: {str(e)}")
                    continue
                    
            return named_ranges
            
        except Exception as e:
            print(f"Warning: Error extracting named ranges: {str(e)}")
            return []
            
    def _get_theme_colors(self) -> Dict[str, str]:
        """Get theme colors from the workbook"""
        try:
            # Default theme colors (Office theme)
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
        except Exception as e:
            print(f"Warning: Error getting theme colors: {str(e)}")
            return {}
            
    def extract_to_json_string(self, workbook_path: Optional[str] = None, output_path: Optional[str] = None, 
                       max_rows_per_sheet: int = 100, max_cols_per_sheet: int = 50) -> str:
        """
        Extract metadata and return as JSON string.
        
        Args:
            workbook_path: Path to the Excel file
            output_path: Optional path to save JSON file
            max_rows_per_sheet: Maximum number of rows to extract per sheet
            max_cols_per_sheet: Maximum number of columns to extract per sheet
            
        Returns:
            JSON string containing the metadata
        """
        metadata = self.extract_workbook_metadata(workbook_path, max_rows_per_sheet, max_cols_per_sheet)
        json_str = json.dumps(metadata, indent=2, ensure_ascii=False)
        
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(json_str)
            print(f"Metadata saved to: {output_path}")
    
            
        return json_str

