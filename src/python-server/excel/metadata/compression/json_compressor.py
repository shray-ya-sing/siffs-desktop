import json
from typing import Dict, Any, List, Optional


class JsonCompressor:
    """
    Compresses Excel metadata into a compact JSON format.
    Expects metadata in the format returned by ExcelMetadataExtractor.extract_workbook_metadata_openpyxl()
    """

    def compress_to_json(
        self,
        metadata: Dict[str, Any],
        output_path: Optional[str] = None,
        indent: Optional[int] = None
    ) -> str:
        """
        Compress Excel metadata into a compact JSON string.

        Args:
            metadata: Dictionary containing workbook metadata from ExcelMetadataExtractor
            output_path: Optional path to save the JSON file
            indent: Number of spaces for indentation (None for most compact)

        Returns:
            JSON string with compressed metadata
        """
        # Compress the metadata structure
        compressed = self._compress_metadata(metadata)
        
        # Convert to JSON with specified formatting
        json_str = json.dumps(
            compressed,
            indent=indent,
            separators=None if indent else (',', ':'),
            ensure_ascii=False
        )

        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(json_str)
            print(f"Compressed JSON saved to: {output_path}")

        return json_str

    def _compress_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compress the full metadata structure to minimize size while maintaining readability.

        Args:
            metadata: Full metadata dictionary

        Returns:
            Compressed metadata dictionary
        """
        return {
            "workbook": self._compress_workbook_info(metadata),
            "sheets": self._compress_sheets(metadata.get("sheets", [])),
            "extractedAt": metadata.get("extractedAt", "")
        }

    def _compress_workbook_info(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Compress workbook-level information."""
        return {
            "name": metadata.get("workbookName", ""),
            "path": metadata.get("workbookPath", ""),
            "activeSheet": metadata.get("activeSheet", ""),
            "totalSheets": metadata.get("totalSheets", 0),
            "sheetNames": metadata.get("sheetNames", [])
        }

    def _compress_sheets(self, sheets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Compress metadata for all sheets."""
        return [self._compress_sheet(sheet) for sheet in sheets]

    def _compress_sheet(self, sheet: Dict[str, Any]) -> Dict[str, Any]:
        """Compress a single sheet's metadata."""
        if sheet.get("isEmpty", True):
            return {
                "name": sheet.get("name", ""),
                "isEmpty": True
            }

        return {
            "name": sheet.get("name", ""),
            "dimensions": {
                "rows": sheet.get("rowCount", 0),
                "columns": sheet.get("columnCount", 0),
                "extractedRows": sheet.get("extractedRowCount", 0),
                "extractedColumns": sheet.get("extractedColumnCount", 0)
            },
            "cells": self._compress_cells(sheet.get("cellData", [])),
            "tables": self._compress_tables(sheet.get("tables", [])),
            "namedRanges": self._compress_named_ranges(sheet.get("namedRanges", []))
        }

    def _compress_cells(self, cell_data: List[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """
        Compress cell data to include only significant cells and properties.

        Args:
            cell_data: 2D array of cell objects

        Returns:
            List of compressed cell objects
        """
        compressed = []
        
        for row_data in cell_data:
            for cell in row_data:
                if self._is_significant_cell(cell):
                    compressed_cell = self._compress_cell(cell)
                    if compressed_cell:
                        compressed.append(compressed_cell)
        
        return compressed

    def _compress_cell(self, cell: Dict[str, Any]) -> Dict[str, Any]:
        """Compress a single cell's data."""
        compressed = {
            "r": cell.get("row"),
            "c": cell.get("column")
        }

        # Add value if present
        value = cell.get("value")
        if value is not None and value != "":
            compressed["v"] = value

        # Add formula if present and different from value
        formula = cell.get("formula")
        if formula and formula != str(value):
            compressed["f"] = formula

        # Add compressed formatting if significant
        formatting = self._compress_formatting(cell.get("formatting", {}))
        if formatting:
            compressed["fmt"] = formatting

        return compressed

    def _compress_formatting(self, formatting: Dict[str, Any]) -> Dict[str, Any]:
        """Compress cell formatting to minimal representation."""
        compressed = {}
        if not formatting:
            return compressed

        # Font properties
        font = formatting.get("font", {})
        if font:
            font_fmt = {}
            if font.get("bold"):
                font_fmt["b"] = 1
            if font.get("italic"):
                font_fmt["i"] = 1
            if font.get("color"):
                font_fmt["c"] = font["color"]
            if font.get("size") and font["size"] != 11:  # Default size
                font_fmt["s"] = font["size"]
            if font_fmt:
                compressed["f"] = font_fmt

        # Fill
        fill = formatting.get("fill", {})
        if fill and fill.get("startColor"):
            compressed["bg"] = fill["startColor"]

        # Number format
        num_fmt = formatting.get("numberFormat")
        if num_fmt and num_fmt.lower() not in ("general", "@"):
            compressed["n"] = num_fmt

        # Alignment
        align = formatting.get("alignment", {})
        if align:
            align_fmt = {}
            if align.get("horizontal"):
                align_fmt["h"] = align["horizontal"][0]  # First letter
            if align.get("vertical"):
                align_fmt["v"] = align["vertical"][0]  # First letter
            if align.get("wrapText"):
                align_fmt["w"] = 1
            if align_fmt:
                compressed["a"] = align_fmt

        # Borders
        borders = formatting.get("borders", {})
        if borders:
            border_fmt = []
            for side, border in borders.items():
                if isinstance(border, dict) and border.get("style"):
                    border_fmt.append(side[0])  # First letter
            if border_fmt:
                compressed["b"] = "".join(sorted(border_fmt))

        # Merged cells
        merged = formatting.get("merged", {})
        if merged and merged.get("isMerged"):
            compressed["m"] = 1
            if merged.get("mergeRange"):
                compressed["mr"] = merged["mergeRange"]

        # Hyperlink
        hyperlink = formatting.get("hyperlink", {})
        if hyperlink and hyperlink.get("target"):
            compressed["h"] = hyperlink["target"]

        # Comment
        comment = formatting.get("comment", {})
        if comment and comment.get("text"):
            compressed["cmt"] = comment["text"][:100]  # Limit comment length

        return compressed

    def _is_significant_cell(self, cell: Dict[str, Any]) -> bool:
        """Determine if a cell contains significant data worth including."""
        # Check for non-empty value or formula
        if cell.get("value") not in (None, ""):
            return True
        if cell.get("formula"):
            return True
            
        # Check for any formatting
        formatting = cell.get("formatting", {})
        return any(key in formatting for key in ["font", "fill", "borders", "alignment"])

    def _compress_tables(self, tables: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Compress table metadata."""
        return [self._compress_table(table) for table in tables]

    def _compress_table(self, table: Dict[str, Any]) -> Dict[str, Any]:
        """Compress a single table's metadata."""
        return {
            "name": table.get("name", ""),
            "range": table.get("range", ""),
            "displayName": table.get("displayName", ""),
            "columns": [col.get("name", "") for col in table.get("columns", [])][:10]  # Limit columns
        }

    def _compress_named_ranges(self, named_ranges: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Compress named ranges metadata."""
        return [self._compress_named_range(nr) for nr in named_ranges]

    def _compress_named_range(self, named_range: Dict[str, Any]) -> Dict[str, Any]:
        """Compress a single named range's metadata."""
        return {
            "name": named_range.get("name", ""),
            "value": named_range.get("value", ""),
            "hidden": named_range.get("hidden", False)
        }