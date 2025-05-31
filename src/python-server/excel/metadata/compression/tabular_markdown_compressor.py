from typing import Dict, Any, Optional


class TabularMarkdownCompressor:
    """
    Compresses Excel metadata into a tabular markdown format.
    Expects metadata in the format returned by ExcelMetadataExtractor.extract_workbook_metadata_openpyxl()
    """

    def compress_to_markdown(
        self,
        metadata: Dict[str, Any],
        output_path: Optional[str] = None
    ) -> str:
        """
        Convert Excel metadata into a compact markdown table format.

        Args:
            metadata: Dictionary containing workbook metadata from ExcelMetadataExtractor
            output_path: Optional path to save the markdown file

        Returns:
            Markdown string with cell data in table format
        """
        markdown_lines = [
            f"# Workbook: {metadata.get('workbookName', '')}",
            f"Active Sheet: {metadata.get('activeSheet', '')}",
            f"Total Sheets: {metadata.get('totalSheets', 0)}",
            f"Extracted At: {metadata.get('extractedAt', '')}",
            ""
        ]

        for sheet in metadata.get("sheets", []):
            if sheet.get("isEmpty", True):
                continue

            markdown_lines.extend([
                f"## Sheet: {sheet.get('name', '')}",
                f"Dimensions: {sheet.get('rowCount', 0)} rows × {sheet.get('columnCount', 0)} columns",
                f"Extracted Range: {sheet.get('extractedRowCount', 0)} rows × {sheet.get('extractedColumnCount', 0)} columns",
                ""
            ])

            # Process cell data
            significant_cells = []
            for row_data in sheet.get("cellData", []):
                for cell in row_data:
                    if self._is_significant_cell(cell):
                        significant_cells.append(cell)

            if significant_cells:
                # Create markdown table header
                markdown_lines.extend([
                    "| Address | Value | Formula | Fill | Font | Style | Borders | Alignment | Merged |",
                    "|---------|-------|---------|------|------|-------|---------|------------|--------|"
                ])

                for cell in significant_cells:
                    row_data = self._format_cell_row(cell)
                    markdown_lines.append("| " + " | ".join(row_data) + " |")

            # Add tables info
            self._add_tables_section(markdown_lines, sheet)
            
            # Add named ranges info
            self._add_named_ranges_section(markdown_lines, sheet)

            markdown_lines.append("")

        markdown_string = "\n".join(markdown_lines)

        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(markdown_string)
            print(f"Markdown saved to: {output_path}")

        return markdown_string

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

    def _format_cell_row(self, cell: Dict[str, Any]) -> list:
        """Format a single cell's data into a markdown table row."""
        formatting = cell.get("formatting", {})
        font = formatting.get("font", {})
        fill = formatting.get("fill", {})
        alignment = formatting.get("alignment", {})
        borders = formatting.get("borders", {})
        merged = formatting.get("merged", {})

        # Format cell address
        row = cell.get("row", "")
        col = cell.get("column", "")
        address = f"R{row}C{col}"

        # Format value and formula
        value = str(cell.get("value", "")) if cell.get("value") is not None else ""
        formula = f'"{cell["formula"]}"' if cell.get("formula") else ""

        # Format fill color
        fill_color = fill.get("startColor", "") if fill.get("startColor") != "auto" else ""

        # Format font info
        font_info = []
        if font.get("color"):
            font_info.append(f"color:{font['color']}")
        if font.get("bold"):
            font_info.append("bold")
        if font.get("italic"):
            font_info.append("italic")
        if font.get("size"):
            font_info.append(f"size:{font['size']}")
        font_str = " ".join(font_info)

        # Format borders
        border_sides = []
        for side, border in borders.items():
            if isinstance(border, dict) and border.get("style"):
                border_sides.append(side[0].upper())
        border_str = "".join(sorted(border_sides))

        # Format alignment
        align_info = []
        if alignment.get("horizontal"):
            align_info.append(f"H:{alignment['horizontal']}")
        if alignment.get("vertical"):
            align_info.append(f"V:{alignment['vertical']}")
        if alignment.get("wrapText"):
            align_info.append("wrap")
        align_str = " ".join(align_info)

        return [
            address,
            value[:50],  # Limit value length
            formula,
            fill_color,
            font_str,
            f"Fmt:{formatting.get('numberFormat', '')}",
            border_str,
            align_str,
            "Y" if merged.get("isMerged") else ""
        ]

    def _add_tables_section(self, markdown_lines: list, sheet: Dict[str, Any]) -> None:
        """Add tables section to markdown if sheet has tables."""
        tables = sheet.get("tables", [])
        if tables:
            markdown_lines.extend(["", "### Tables:", ""])
            for table in tables:
                name = table.get("name", "Unnamed")
                table_range = table.get("range", "Unknown")
                columns = [col.get("name", "") for col in table.get("columns", [])]
                markdown_lines.append(f"- **{name}** ({table_range}): {', '.join(columns[:5])}")

    def _add_named_ranges_section(self, markdown_lines: list, sheet: Dict[str, Any]) -> None:
        """Add named ranges section to markdown if sheet has named ranges."""
        named_ranges = sheet.get("namedRanges", [])
        if named_ranges:
            markdown_lines.extend(["", "### Named Ranges:", ""])
            for nr in named_ranges:
                name = nr.get("name", "Unnamed")
                ref = nr.get("value", "Unknown")
                markdown_lines.append(f"- **{name}**: {ref}")