from typing import Dict, List, Any, Optional, Tuple
import json
import xlwings as xw
from datetime import datetime
import uuid
import os
from dataclasses import dataclass
from pathlib import Path
import sys
# Add the project root to Python path
folder_path = Path(__file__).parent.parent.parent.absolute()
sys.path.append(str(folder_path))
from metadata.storage.excel_metadata_storage import ExcelMetadataStorage

class StorageUpdater:
    """Handles the final storage update when edits are accepted."""
    
    def __init__(self, storage: 'ExcelMetadataStorage' = None):
        self.storage = storage or ExcelMetadataStorage()
    
    def update_storage(self, 
                      file_path: str,
                      version_id: int, 
                      cell_updates: List[Dict[str, Any]],
                      create_new_version: bool = True) -> int:
        """
        Update storage with accepted cell edits.
        
        Returns:
            int: The version_id that was updated
        """
        try:
            # Ensure workbook exists in storage
            normalized_path = str(Path(file_path).resolve())
            self.storage.create_or_update_workbook(normalized_path)
            
            if create_new_version:
                # Create new version
                new_version_id = self.storage.create_new_version(
                    file_path=normalized_path,
                    change_description=f"Accepted {len(cell_updates)} edits at {datetime.now()}"
                )
                target_version_id = new_version_id
            else:
                target_version_id = version_id
            
            # Transform cell updates to storage format
            storage_updates = []
            for update in cell_updates:
                storage_updates.append({
                    "sheet_name": update['sheet_name'],
                    "cell_address": update['cell_address'],
                    "cell_data": self._transform_to_storage_format(update['cell_data'])
                })
            
            # Update cells in storage (triggers propagation)
            success = self.storage.update_cells(
                version_id=target_version_id,
                cell_updates=storage_updates
            )
            
            return target_version_id if success else None
            
        except Exception as e:
            print(f"Error updating storage: {e}")
            raise
    
    def _transform_to_storage_format(self, cell_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform Excel writer format to storage format."""
        # Handle both 'cell' and 'address' keys
        address = cell_data.get('cell') or cell_data.get('address', '')
        
        return {
            "address": address,
            "value": cell_data.get('value'),
            "formula": cell_data.get('formula'),
            "data_type": self._infer_data_type(cell_data),
            "formatting": self._build_formatting_object(cell_data),
            "is_formula": bool(cell_data.get('formula')),
            "is_array_formula": False,
            "is_merged": False,
            "directPrecedents": [],
            "directDependents": [],
        }
    
    def _infer_data_type(self, cell_data: Dict) -> str:
        """Infer data type from cell data."""
        if cell_data.get('formula'):
            return 'formula'
        
        value = cell_data.get('value')
        if value is None:
            return 'empty'
        elif isinstance(value, bool):
            return 'boolean'
        elif isinstance(value, (int, float)):
            return 'number'
        else:
            return 'string'
    
    def _build_formatting_object(self, cell_data: Dict) -> Dict:
        """Build formatting object from cell data."""
        formatting = {}
        
        # Font formatting
        font_props = {}
        if cell_data.get('bold'):
            font_props['bold'] = True
        if cell_data.get('italic'):
            font_props['italic'] = True
        if 'font_size' in cell_data:
            font_props['size'] = cell_data['font_size']
        if 'font_style' in cell_data:
            font_props['name'] = cell_data['font_style']
        if 'text_color' in cell_data:
            font_props['color'] = cell_data['text_color']
        
        if font_props:
            formatting['font'] = font_props
        
        # Alignment
        alignment = {}
        if 'horizontal_alignment' in cell_data:
            alignment['horizontal'] = cell_data['horizontal_alignment']
        if 'vertical_alignment' in cell_data:
            alignment['vertical'] = cell_data['vertical_alignment']
        if 'wrap_text' in cell_data:
            alignment['wrap_text'] = cell_data['wrap_text']
        
        if alignment:
            formatting['alignment'] = alignment
        
        # Fill
        if 'fill_color' in cell_data and cell_data['fill_color']:
            formatting['fill'] = {'color': cell_data['fill_color']}
        
        # Number format
        if 'number_format' in cell_data:
            formatting['number_format'] = cell_data['number_format']
        
        return formatting

class ExcelPendingEditManager:
    """Manages temporary edits with cell color indicators."""
    
    def __init__(self, storage: 'ExcelMetadataStorage' = None):
        self.storage = storage or ExcelMetadataStorage()
        self.updater = StorageUpdater(self.storage)
        self.pending_edits = {}
        self.edit_indicator_prefix = "PE_"
        # Define indicator colors
        self.PENDING_COLOR = (255, 255, 200)  # Light yellow for pending
        self.PENDING_WITH_COLOR_COLOR = (200, 255, 200)  # Light green if edit includes color change
    
    def apply_pending_edit(self, 
        wb: xw.Book,
        sheet_name: str,
        cell_data: Dict[str, Any],
        version_id: int,
        file_path: str) -> str:
        """
        Apply an edit directly to the cell without any pending indicators.
        
        Args:
            wb: Excel workbook
            sheet_name: Name of the sheet containing the cell
            cell_data: Dictionary containing cell data including value/formula and formatting
            version_id: Version ID for tracking
            file_path: Path to the workbook file
            
        Returns:
            str: Edit ID for tracking
        """
        edit_id = str(uuid.uuid4())[:8]
        cell_address = cell_data.get('cell', '')
        
        try:
            sheet = wb.sheets[sheet_name]
            cell = sheet.range(cell_address)

            # Apply the edits to the cell, continuing even if one type of edit fails
            try:
                # 1. Apply the value or formula
                if 'formula' in cell_data and cell_data['formula']:
                    cell.formula = cell_data['formula']
                elif 'value' in cell_data:
                    cell.value = cell_data['value']
            except Exception as e:
                print(f"Error applying value to cell {cell_address}: {e}")

            try:
                # 2. Apply all formatting including fill color
                if cell_data:  # Only apply formatting if cell_data is not empty
                    self._apply_formatting_from_data(cell, cell_data)
            except Exception as e:
                print(f"Error applying formatting to cell {cell_address}: {e}")                
            
            print(f"Applied pending edit to {cell_address} without indicator color")
            return edit_id
            
        except Exception as e:
            print(f"Error applying pending edit: {e}")
            raise
    
    def apply_pending_edit_with_separate_color_indicator(self, 
        wb: xw.Book,
        sheet_name: str,
        cell_data: Dict[str, Any],
        version_id: int,
        file_path: str) -> str:
        """Apply a pending edit with separate color indicator."""
        edit_id = str(uuid.uuid4())[:8]
        cell_address = cell_data.get('cell', '')
        
        try:
            sheet = wb.sheets[sheet_name]
            cell = sheet.range(cell_address)
            
            # 1. Capture original state (including original color)
            original_state = self._capture_cell_state(cell)
            
            # 2. Extract intended fill_color from cell_data if present
            intended_fill_color = cell_data.get('fill_color')
            
            # 3. Create a copy of cell_data without fill_color for initial application
            cell_data_without_color = cell_data.copy()
            if 'fill_color' in cell_data_without_color:
                del cell_data_without_color['fill_color']
            
            # 4. Apply the edit WITHOUT the fill color
            if 'formula' in cell_data and cell_data['formula']:
                cell.formula = cell_data['formula']
            elif 'value' in cell_data:
                cell.value = cell_data['value']
            
            # Apply formatting EXCEPT fill color
            self._apply_formatting_from_data(cell, cell_data_without_color)
            
            # 5. Apply indicator color instead
            if intended_fill_color:
                # Use green indicator if edit includes a color change
                cell.color = self.PENDING_WITH_COLOR_COLOR
            else:
                # Use yellow indicator for edits without color change
                cell.color = self.PENDING_COLOR
            
            # 6. Store the pending edit with all data including intended color
            self._create_pending_edit(
                version_id=version_id,
                sheet_name=sheet_name,
                cell_address=cell_address,
                original_state=original_state,
                cell_data=cell_data,  # This includes the intended fill_color
                edit_id=edit_id,
                file_path=file_path,
                intended_fill_color=intended_fill_color  # Store separately for clarity
            )
            
            print(f"Applied pending edit to {cell_address} with indicator color")
            return edit_id
            
        except Exception as e:
            print(f"Error applying pending edit: {e}")
            raise


    def apply_pending_edit_with_color_indicator(self, 
        wb: xw.Book,
        sheet_name: str,
        cell_data: Dict[str, Any],
        version_id: int,
        file_path: str) -> str:
        """Apply a pending edit with a green color indicator."""
        edit_id = str(uuid.uuid4())[:8]
        cell_address = cell_data.get('cell', '')
        
        try:
            sheet = wb.sheets[sheet_name]
            cell = sheet.range(cell_address)
            
            # 1. Capture original state
            original_state = self._capture_cell_state(cell)
            
            # 2. Extract intended fill_color from cell_data if present
            intended_fill_color = cell_data.get('fill_color')
            
            # 3. Apply the edit without the fill color
            if 'formula' in cell_data and cell_data['formula']:
                cell.formula = cell_data['formula']
            elif 'value' in cell_data:
                cell.value = cell_data['value']
            
            # 4. Apply all formatting EXCEPT fill color
            cell_data_without_color = {k: v for k, v in cell_data.items() if k != 'fill_color'}
            self._apply_formatting_from_data(cell, cell_data_without_color)
            
            # 5. Apply green indicator color to all pending edits
            cell.color = self.PENDING_WITH_COLOR_COLOR  # Always use green
            
            # 6. Store the pending edit with all data
            self._create_pending_edit(
                version_id=version_id,
                sheet_name=sheet_name,
                cell_address=cell_address,
                original_state=original_state,
                cell_data=cell_data,  # Includes the intended fill_color
                edit_id=edit_id,
                file_path=file_path,
                intended_fill_color=intended_fill_color
            )
            
            print(f"Applied pending edit to {cell_address} with green indicator")
            return edit_id
            
        except Exception as e:
            print(f"Error applying pending edit: {e}")
            raise
    
    
    def accept_edit(self, 
                    wb: xw.Book,
                    version_id: int,
                    sheet_name: str,
                    cell_address: str,
                    create_new_version: bool = True) -> bool:
        """Accept a pending edit and apply intended formatting."""
        try:
            edit = self._get_pending_edit(version_id, sheet_name, cell_address)
            if not edit:
                print(f"No pending edit found for {sheet_name}!{cell_address}")
                return False
            
            sheet = wb.sheets[sheet_name]
            cell = sheet.range(cell_address)
            
            # Remove indicator color and apply intended color
            intended_color = edit.get('intended_fill_color')
            if intended_color:
                # Apply the intended fill color
                cell.color = intended_color
                print(f"Applied intended color {intended_color} to {cell_address}")
            else:
                # Restore original color if no color was intended
                original_color = edit['original_state'].get('fill_color')
                if original_color:
                    cell.color = original_color
                else:
                    # Clear color if originally had none
                    cell.color = None
            
            # Update storage
            cell_updates = [{
                'sheet_name': sheet_name,
                'cell_address': cell_address,
                'cell_data': edit['cell_data']
            }]
            
            updated_version = self.updater.update_storage(
                file_path=edit['file_path'],
                version_id=version_id,
                cell_updates=cell_updates,
                create_new_version=create_new_version
            )
            
            if updated_version:
                self._remove_pending_edit(version_id, sheet_name, cell_address)
                return True
            
            return False
            
        except Exception as e:
            print(f"Error accepting edit: {e}")
            return False
    
    def reject_edit(self,
                   wb: xw.Book,
                   version_id: int,
                   sheet_name: str,
                   cell_address: str) -> bool:
        """Reject a pending edit and restore original state."""
        try:
            edit = self._get_pending_edit(version_id, sheet_name, cell_address)
            if not edit:
                print(f"No pending edit found for {sheet_name}!{cell_address}")
                return False
            
            sheet = wb.sheets[sheet_name]
            cell = sheet.range(cell_address)
            
            # Restore original state
            original = edit['original_state']
            
            # Restore value/formula
            if original.get('formula'):
                cell.formula = original['formula']
            else:
                cell.value = original.get('value')
            
            # Restore ALL formatting including color
            self._restore_cell_state(cell, original)
            
            # Remove from pending edits
            self._remove_pending_edit(version_id, sheet_name, cell_address)
            
            print(f"Rejected edit and restored original state for {cell_address}")
            return True
            
        except Exception as e:
            print(f"Error rejecting edit: {e}")
            return False
    
    def accept_all_edits(self,
                        wb: xw.Book,
                        version_id: int,
                        sheet_name: str = None,
                        create_new_version: bool = True) -> bool:
        """Accept all pending edits efficiently."""
        try:
            pending = self._get_all_pending_for_version(version_id, sheet_name)
            
            if not pending:
                print("No pending edits to accept")
                return True
            
            # Apply all intended colors and prepare updates
            cell_updates = []
            for edit in pending:
                try:
                    sheet = wb.sheets[edit['sheet_name']]
                    cell = sheet.range(edit['cell_address'])
                    
                    # Apply intended color or restore original
                    intended_color = edit.get('intended_fill_color')
                    if intended_color:
                        cell.color = intended_color
                    else:
                        original_color = edit['original_state'].get('fill_color')
                        if original_color:
                            cell.color = original_color
                        else:
                            cell.color = None
                    
                    cell_updates.append({
                        'sheet_name': edit['sheet_name'],
                        'cell_address': edit['cell_address'],
                        'cell_data': edit['cell_data']
                    })
                    
                except Exception as e:
                    print(f"Warning: Could not process {edit['cell_address']}: {e}")
            
            # Batch update storage
            file_path = pending[0]['file_path'] if pending else None
            updated_version = self.updater.update_storage(
                file_path=file_path,
                version_id=version_id,
                cell_updates=cell_updates,
                create_new_version=create_new_version
            )
            
            if updated_version:
                # Clear pending edits
                for edit in pending:
                    self._remove_pending_edit(
                        version_id, 
                        edit['sheet_name'], 
                        edit['cell_address']
                    )
                return True
            
            return False
            
        except Exception as e:
            print(f"Error accepting all edits: {e}")
            return False

    def get_pending_edit_summary(self, wb: xw.Book, version_id: int) -> List[Dict]:
        """Get a summary of all pending edits with visual status."""
        pending = self._get_all_pending_for_version(version_id)
        summary = []
        
        for edit in pending:
            try:
                sheet = wb.sheets[edit['sheet_name']]
                cell = sheet.range(edit['cell_address'])
                
                # Check current color to verify it's still pending
                current_color = cell.color
                is_pending = (current_color == self.PENDING_COLOR or 
                             current_color == self.PENDING_WITH_COLOR_COLOR)
                
                summary.append({
                    'sheet_name': edit['sheet_name'],
                    'cell_address': edit['cell_address'],
                    'edit_id': edit['edit_id'],
                    'has_color_change': bool(edit.get('intended_fill_color')),
                    'is_pending': is_pending,
                    'original_value': edit['original_state'].get('value'),
                    'new_value': edit['cell_data'].get('value') or edit['cell_data'].get('formula')
                })
            except:
                continue
                
        return summary

    def _apply_formatting_from_data(self, cell: xw.Range, cell_data: Dict):
        """Apply formatting from cell data dict (excluding fill_color if using indicators)."""
        try:
            if cell_data.get('bold'):
                cell.font.bold = True
            if cell_data.get('italic'):
                cell.font.italic = True
            if 'font_size' in cell_data and cell_data['font_size']:
                cell.font.size = cell_data['font_size']
            if 'font_style' in cell_data and cell_data['font_style']:
                cell.font.name = cell_data['font_style']
            if 'text_color' in cell_data and cell_data['text_color']:
                cell.font.color = cell_data['text_color']
            # Note: fill_color is handled separately in the indicator logic
            if 'number_format' in cell_data and cell_data['number_format']:
                cell.number_format = cell_data['number_format']
        except Exception as e:
            print(f"Warning: Some formatting could not be applied: {e}")

    def _capture_cell_state(self, cell: xw.Range) -> Dict[str, Any]:
        """Capture the current state of a cell before editing."""
        state = {
            "value": cell.value,
            "formula": cell.formula if cell.formula else None,
            "number_format": cell.number_format
        }
        
        # Capture formatting - some properties might not be available on Mac
        try:
            state.update({
                "font_name": cell.font.name,
                "font_size": cell.font.size,
                "font_bold": cell.font.bold,
                "font_italic": cell.font.italic,
                "font_color": cell.font.color,
                "fill_color": cell.color
            })
        except Exception as e:
            print(f"Warning: Some cell properties could not be captured: {e}")
        
        return state
    
    def reject_all_edits(self,
                        wb: xw.Book,
                        version_id: int,
                        sheet_name: str = None) -> bool:
        """Reject all pending edits and revert to original state."""
        try:
            pending = self._get_all_pending_for_version(version_id, sheet_name)
            
            if not pending:
                print("No pending edits to reject")
                return True  # Fixed indentation
            
            # Create a copy of the list to avoid modifying it during iteration
            pending_edits = list(pending)
            success = True
            
            for edit in pending_edits:
                # Reuse the reject_edit method for each pending edit
                result = self.reject_edit(
                    wb=wb,
                    version_id=version_id,
                    sheet_name=edit['sheet_name'],
                    cell_address=edit['cell_address']
                )
                
                if not result:
                    success = False
                    print(f"Failed to reject edit at {edit['sheet_name']}!{edit['cell_address']}")
            
            return success
            
        except Exception as e:
            print(f"Error in reject_all_edits: {e}")
            return False

    def _restore_cell_state(self, cell: xw.Range, state: Dict[str, Any]):
        """Restore a cell to its original state."""
        try:
            # Restore formatting
            if 'number_format' in state and state['number_format']:
                cell.number_format = state['number_format']
            if 'font_name' in state and state['font_name']:
                cell.font.name = state['font_name']
            if 'font_size' in state and state['font_size'] is not None:
                cell.font.size = state['font_size']
            if 'font_bold' in state and state['font_bold'] is not None:
                cell.font.bold = state['font_bold']
            if 'font_italic' in state and state['font_italic'] is not None:
                cell.font.italic = state['font_italic']
            if 'font_color' in state and state['font_color']:
                cell.font.color = state['font_color']
            if 'fill_color' in state and state['fill_color']:
                cell.color = state['fill_color']
        except Exception as e:
            print(f"Warning: Some formatting could not be restored: {e}") 

    
    def _create_pending_edit(self, **kwargs):
        """Store a pending edit record."""
        version_id = kwargs['version_id']
        if version_id not in self.pending_edits:
            self.pending_edits[version_id] = {}
        
        key = f"{kwargs['sheet_name']}!{kwargs['cell_address']}"
        self.pending_edits[version_id][key] = {
            'timestamp': datetime.now().isoformat(),
            **kwargs
        }
    
    def _get_pending_edit(self, version_id: int, sheet_name: str, 
                         cell_address: str) -> Optional[Dict]:
        """Get a pending edit record."""
        if version_id not in self.pending_edits:
            return None
        
        key = f"{sheet_name}!{cell_address}"
        return self.pending_edits[version_id].get(key)
    
    def _remove_pending_edit(self, version_id: int, sheet_name: str, 
                            cell_address: str):
        """Remove a pending edit record."""
        if version_id in self.pending_edits:
            key = f"{sheet_name}!{cell_address}"
            self.pending_edits[version_id].pop(key, None)
    
    def _get_all_pending_for_version(self, version_id: int, 
                                    sheet_name: str = None) -> List[Dict]:
        """Get all pending edits for a version."""
        if version_id not in self.pending_edits:
            return []
        
        pending = []
        for key, edit in self.pending_edits[version_id].items():
            if sheet_name and edit['sheet_name'] != sheet_name:
                continue
            pending.append(edit)
        
        return pending