from typing import Dict, List, Any, Optional, Tuple
import json
import xlwings as xw
from datetime import datetime
import uuid
import os
import time
from dataclasses import dataclass
from pathlib import Path
import sys
import tempfile
# Add the project root to Python path
folder_path = Path(__file__).parent.parent.parent.absolute()
sys.path.append(str(folder_path))
from metadata.storage.excel_metadata_storage import ExcelMetadataStorage
from session_management.excel_session_manager import ExcelSessionManager
import logging
logger = logging.getLogger(__name__)

class StorageUpdater:
    """Handles the final storage update when edits are accepted."""
    
    def __init__(self, 
                 storage: 'ExcelMetadataStorage' = None):
        self.storage = storage or ExcelMetadataStorage()


    def update_storage(self, 
                  file_path: str,
                  version_ids: List[int], 
                  cell_updates: List[Dict[str, Any]],
                  create_new_version: bool = True,
                  file_blob_paths_to_store: Dict[int, str] = None) -> List[int]:
        """
        Update storage with accepted cell edits for multiple versions.
        
        Args:
            file_path: Path to the workbook
            version_ids: List of version IDs to update
            cell_updates: List of cell updates to apply
            create_new_version: Whether to create new versions for the updates
            file_blob_paths_to_store: Dict of version IDs to file paths to store
            
        Returns:
            List of version IDs that were updated
        """
        if not version_ids:
            return []
            
        try:
            # Ensure workbook exists in storage
            normalized_path = str(Path(file_path).resolve())
            self.storage.create_or_update_workbook(normalized_path)
            
            updated_versions = []
            
            # Transform cell updates to storage format once
            storage_updates = []
            for update in cell_updates:
                storage_updates.append({
                    "sheet_name": update['sheet_name'],
                    "cell_address": update['cell_address'],
                    "cell_data": self._transform_to_storage_format(update['cell_data'])
                })
            
            # Process each version
            logger.info(f"Processing {len(version_ids)} versions for storage update")
            for version_id in version_ids:
                try:
                    target_version_id = version_id
                    
                    if create_new_version:
                        if file_blob_paths_to_store:
                            file_blob_copy_path = file_blob_paths_to_store.get(version_id)
                        else:
                            file_blob_copy_path = None
                        # Create new version based on the current version
                        new_version_id = self.storage.create_new_version(
                            file_path=normalized_path,
                            change_description=f"Accepted {len(cell_updates)} edits at {datetime.now()}",
                            store_file_blob_copy=True,
                            file_blob_copy_path=file_blob_copy_path                            
                        )
                        target_version_id = new_version_id
                        logger.info(f"Created new version {new_version_id} for storage update")
                    
                    # Update cell metadata in storage
                    logger.info(f"Updating cells in storage for version {target_version_id}")
                    try:
                        success = self.storage.update_cells(
                            file_path=normalized_path,
                            version_id=target_version_id,
                            cell_updates=storage_updates
                        )
                    
                        if success:
                            updated_versions.append(target_version_id)
                            logger.info(f"Successfully updated cells in storage for version {target_version_id}")
                        else:
                            logger.warning(f"Failed to update cells in storage for version {target_version_id}")
                    except Exception as e:
                        logger.error(f"Error updating cells in storage: {e}")
                        continue
                    
                except Exception as e:
                    logger.error(f"Error updating version {version_id}: {e}")
                    continue
                    
            return updated_versions
            
        except Exception as e:
            logger.error(f"Error in update_storage: {e}")
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
    
    def __init__(self, 
                 storage: 'ExcelMetadataStorage' = None,
                 session_manager: 'ExcelSessionManager' = None):
        self.storage = storage or ExcelMetadataStorage()
        self.updater = StorageUpdater(self.storage)
        self.session_manager = session_manager or ExcelSessionManager()
        self.edit_indicator_prefix = "PE_"
        # Define indicator colors
        self.PENDING_COLOR = (255, 255, 200)  # Light yellow for pending
        self.PENDING_WITH_COLOR_COLOR = (200, 255, 200)  # Light green if edit includes color change
        self.visible = True
    
    def apply_pending_edit(self, 
        wb: xw.Book,
        sheet_name: str,
        cell_data: Dict[str, Any],
        version_id: int,
        file_path: str) -> Dict[str, Any]:
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
                logger.error(f"Error applying value to cell {cell_address}: {e}")

            try:
                # 2. Apply all formatting including fill color
                if cell_data:  # Only apply formatting if cell_data is not empty
                    self._apply_formatting_from_data(cell, cell_data)
            except Exception as e:
                logger.error(f"Error applying formatting to cell {cell_address}: {e}")                
            
            logger.info(f"Applied pending edit to {cell_address} without indicator color")
            return {"edit_id": edit_id}
            
        except Exception as e:
            logger.error(f"Error applying pending edit: {e}")
            raise
    
    def apply_pending_edit_with_color_indicator(self, 
        wb: xw.Book,
        sheet_name: str,
        cell_data: Dict[str, Any],
        version_id: int,
        file_path: str) -> Dict[str, Any]:
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
            edit_dict = self._create_pending_edit(
                version_id=version_id,
                sheet_name=sheet_name,
                cell_address=cell_address,
                original_state=original_state,
                cell_data=cell_data,  # Includes the intended fill_color
                edit_id=edit_id,
                file_path=file_path,
                intended_fill_color=intended_fill_color
            )
            
            logger.info(f"Applied pending edit to {cell_address} with green indicator")
            return edit_dict
            
        except Exception as e:
            logger.error(f"Error applying pending edit: {e}")
            raise


    # ACCEPTING / REJECTING EDITS-------------------------------------------------------------------------------------------------------------------------------------

    def accept_edits(
        self,
        edit_ids: List[str],
        create_new_version: bool = True
    ) -> Dict[str, Any]:
        """
        Accept multiple pending edits by their IDs, update storage, and apply changes to the workbook.
        
        Args:
            edit_ids: List of edit IDs to accept
            create_new_version: Whether to create a new version in storage
            
        Returns:
            Dictionary containing:
            - 'success': Whether the operation completed successfully
            - 'accepted_count': Number of edits successfully accepted
            - 'failed_ids': List of edit IDs that failed to be accepted
            - 'accepted_edit_version_ids': The version IDs that were updated
        """
        if not edit_ids:
            return {
                'success': False,
                'accepted_count': 0,
                'failed_ids': [],
                'accepted_edit_version_ids': None
            }
        
        try:
            # Batch update status in storage to change status to accepted
            result = self.storage.batch_update_edit_statuses(
                edit_ids=edit_ids,
                new_status='accepted'
            )
            
            if not result or 'updated_count' not in result:
                return {
                    'success': False,
                    'accepted_count': 0,
                    'failed_ids': edit_ids,
                    'accepted_edit_version_ids': None
                }
            
            logger.info(f"Batch updated {result['updated_count']} edits to accepted status")
            # Replace the cell updates preparation with:
            cell_updates = []
            successful_edits = result.get('edits', [])

            accepted_edits_version_ids = [] # Account for the scenario where edits across multiple versions get accepted
            # Multiple versions should never happen but we have to be certain

            # Group edits by file path to minimize session operations
            edits_by_file = {}
            for edit in successful_edits:
                file_path = edit['file_path']
                if file_path not in edits_by_file:
                    edits_by_file[file_path] = []
                edits_by_file[file_path].append(edit)

            for file_path, file_edits in edits_by_file.items():
                try:
                    # Process storage updates
                    version_ids = set()
                    # Get the xlwings workbook object to perform edits in wb
                    wb = self.get_workbook_from_session_manager(file_path)

                    for edit in file_edits:
                        
                        version_id = edit.get('version_id')
                        if version_id:
                            version_ids.add(version_id)

                        try:
                            cell_updates.append({
                                'sheet_name': edit['sheet_name'],
                                'cell_address': edit['cell_address'],
                                'cell_data': json.loads(edit['cell_data'])
                            })

                            logger.info(f"Appended cell update for edit {edit.get('edit_id')}")
                        except (KeyError, json.JSONDecodeError) as e:
                            logger.error(f"Error appending cell update for edit {edit.get('edit_id')}: {e}")
                            if 'failed_ids' not in result:
                                result['failed_ids'] = []
                            result['failed_ids'].append(edit.get('edit_id'))
                            result['updated_count'] = max(0, result.get('updated_count', 0) - 1)

                        # Apply changes to the workbook
                        try:                            
                            sheet = wb.sheets[edit['sheet_name']]
                            cell = sheet.range(edit['cell_address'])
                            
                            # Apply the intended fill color if it exists
                            intended_color = edit.get('intended_fill_color')
                            if intended_color:
                                cell.color = intended_color
                                logger.info(f"Applied intended fill color {intended_color} for edit {edit['edit_id']} to cell {cell} on {sheet} in workbook")
                            else:
                                # Restore original color if no color was intended
                                original_state = json.loads(edit.get('original_state', '{}'))
                                original_color = original_state.get('fill_color')
                                if original_color:
                                    cell.color = original_color
                                    logger.info(f"Applied original fill color {original_color} for edit {edit['edit_id']} to cell {cell} on {sheet} in workbook")
                                else:
                                    cell.color = (255, 255, 255)
                                    logger.info(f"No original fill color found for edit {edit['edit_id']} to cell {cell} on {sheet} in workbook. Applying white color instead.")
                            

                                    
                        except Exception as e:
                            logger.error(f"Error applying original fill color for edit {edit['edit_id']} to workbook: {e}")
                            if 'failed_ids' not in result:
                                result['failed_ids'] = []
                            result['failed_ids'].append(edit.get('edit_id'))
                            result['updated_count'] = max(0, result.get('updated_count', 0) - 1)

                except Exception as e:
                    logger.error(f"Error processing accepted edits for file {file_path}: {e}")

                file_blob_paths_to_store = {} # Dict with {version id: filepath}
                for version_id in version_ids:
                    # Store a copy of the file with the accepted edits to save as a blob for version management in db 
                    try:
                        # Create a normalized filename with version and timestamp
                        copy_version_id = version_id + 1
                        file_stem = Path(file_path).stem
                        file_name = f"{file_stem}_version_{copy_version_id}_{int(time.time())}.xlsx"
                        version_dir = Path(tempfile.gettempdir()) / "excel_versions"
                        version_dir.mkdir(exist_ok=True)  # Create directory if it doesn't exist
                        saved_copy_path = str(version_dir / file_name)
                        wb.save(saved_copy_path)  # Creates copy on disk, doesn't open it
                        # Immediately close the copy so we can access it later

                        file_blob_paths_to_store[version_id] = saved_copy_path
                    except Exception as e:
                        logger.error(f"Error storing file blob for prev version {version_id} new version {copy_version_id}: {e}")
                # If we have any successful updates, update the storage metadata to reflect updated excel file metadata                
                if cell_updates and self.storage and version_ids:
                    try:                                         
                        # Update storage with the accepted changes
                        self.updater.update_storage(
                            file_path=file_path,
                            version_ids=version_ids,
                            cell_updates=cell_updates,
                            create_new_version=create_new_version or True,
                            file_blob_paths_to_store=file_blob_paths_to_store
                        )
                        accepted_edits_version_ids.extend(version_ids)
                        logger.info(f"Successfully updated storage metadata for accepted edits")
                    except Exception as e:
                        logger.error(f"Error updating storage metadata for accepted edits: {e}")
                        # Continue to apply changes to the workbook even if storage update fails
                        if 'failed_ids' not in result:
                            result['failed_ids'] = []
                        result['failed_ids'].append(edit.get('edit_id'))
                        result['updated_count'] = max(0, result.get('updated_count', 0) - 1)
            
            return {
                'success': True,
                'accepted_count': result.get('updated_count', 0),
                'failed_ids': result.get('failed_ids', []),
                'accepted_edit_version_ids': accepted_edits_version_ids
            }
            
        except Exception as e:
            logger.error(f"Error accepting edits: {e}")
            return {
                'success': False,
                'accepted_count': 0,
                'failed_ids': edit_ids,
                'accepted_edit_version_ids': None,
                'error': str(e)
            }

    def reject_edits(
        self,
        edit_ids: List[str]
    ) -> Dict[str, Any]:
        """
        Reject multiple pending edits by their IDs, restoring original cell states.
        
        Args:
            edit_ids: List of edit IDs to reject
            
        Returns:
            Dictionary containing:
            - 'success': Whether the operation completed successfully
            - 'rejected_count': Number of edits successfully rejected
            - 'failed_ids': List of edit IDs that failed to be rejected
        """
        if not edit_ids:
            return {
                'success': False,
                'rejected_count': 0,
                'failed_ids': []
            }
        
        try:
            # Batch update status in storage to change status to rejected
            result = self.storage.batch_update_edit_statuses(
                edit_ids=edit_ids,
                new_status='rejected'
            )
            
            if not result or 'updated_count' not in result:
                return {
                    'success': False,
                    'rejected_count': 0,
                    'failed_ids': edit_ids
                }
            
            logger.info(f"Batch updated {result['updated_count']} edits to rejected status")
            successful_edits = result.get('edits', [])
            failed_ids = []

            # Group edits by file path to minimize session operations
            edits_by_file = {}
            for edit in successful_edits:
                file_path = edit['file_path']
                if file_path not in edits_by_file:
                    edits_by_file[file_path] = []
                edits_by_file[file_path].append(edit)

            for file_path, file_edits in edits_by_file.items():
                try:
                    # Get the xlwings workbook object
                    wb = self.get_workbook_from_session_manager(file_path)
                    
                    for edit in file_edits:
                        try:
                            sheet = wb.sheets[edit['sheet_name']]
                            cell = sheet.range(edit['cell_address'])
                            
                            # Restore original state
                            original_state = json.loads(edit.get('original_state', '{}'))
                            
                            # Restore value/formula
                            if 'formula' in original_state and original_state['formula']:
                                cell.formula = original_state['formula']
                            elif 'value' in original_state:
                                cell.value = original_state['value']
                                
                            # Restore formatting
                            self._restore_cell_state(cell, original_state)
                            
                            logger.info(f"Successfully restored original state for cell {edit['cell_address']}")
                            
                        except Exception as e:
                            logger.error(f"Error restoring cell state for edit {edit.get('edit_id')}: {e}")
                            failed_ids.append(edit.get('edit_id'))
                            result['updated_count'] = max(0, result.get('updated_count', 0) - 1)
                            
                except Exception as e:
                    logger.error(f"Error processing rejected edits for file {file_path}: {e}")
                    # Mark all edits for this file as failed
                    for edit in file_edits:
                        failed_ids.append(edit.get('edit_id'))
                    result['updated_count'] = max(0, result.get('updated_count', 0) - len(file_edits))
            
            return {
                'success': True,
                'rejected_count': result.get('updated_count', 0),
                'failed_ids': failed_ids
            }
            
        except Exception as e:
            logger.error(f"Error rejecting edits: {e}")
            return {
                'success': False,
                'rejected_count': 0,
                'failed_ids': edit_ids,
                'error': str(e)
            }
    

    # HELPER METHODS---------------------------------------------------------------------------------------------------------------------------------------------
    
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
            logger.warning(f"Warning: Some formatting could not be applied: {e}")

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
            logger.warning(f"Warning: Some cell properties could not be captured: {e}")
        
        return state
    
    

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
            if 'fill_color' in state:
                if state['fill_color']:
                    cell.color = state['fill_color']
                else:
                    cell.color = (255, 255, 255) # Set to white
            
        except Exception as e:
            logger.warning(f"Warning: Some formatting could not be restored: {e}") 

    
    def _create_pending_edit(self, **kwargs):
        """Create and return a pending edit dictionary.
        
        Returns:
            dict: The created edit dictionary with timestamp
        """
        edit_dict = {
            'timestamp': datetime.now().isoformat(),
            **kwargs
        }
        return edit_dict

    # This method can only be used for accessing existing workbooks i.e. valid filepaths. 
    # If the file does not exist, it will raise an error.
    def get_workbook_from_session_manager(self, file_path: str) -> xw.Book:
        """Get a workbook from the session manager.
            
            Args:
                file_path (str): The path to the workbook.
            
            Returns:
                xw.Book: The workbook.
        """
        file_path = str(Path(file_path).resolve())
        wb = self.session_manager.get_session(file_path, self.visible)
        if not wb:
            raise RuntimeError(f"Failed to get session for {file_path}. Check filepath validity.")
        return wb
        
    # CONTEXT MANAGER METHODS -------------------------------------------------------------------------------------------------------------------------------------

    def __enter__(self):
        """Context manager entry - return self to be used in the with statement."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - no resource cleanup, just pass through."""
        # Don't suppress any exceptions
        return False