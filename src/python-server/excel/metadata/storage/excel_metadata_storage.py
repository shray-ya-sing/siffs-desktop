from pathlib import Path
import os
import sqlite3
import json
from typing import Optional, List, Dict, Set, Any
import atexit
import threading
import hashlib
from datetime import datetime
import re

import logging
logger = logging.getLogger(__name__)

# Class-level registry to track initialized databases
_initialized_dbs = set()
_initialization_lock = threading.Lock()

class ExcelMetadataStorage:
    _instances = {}
    _instances_lock = threading.Lock()
    
    def __new__(cls, db_path: str = None, db_name: str = "excel_metadata.db"):
        """Implement singleton pattern per database path."""
        if db_path is None:
            base_dir = Path(__file__).parent.parent
            db_path = str(base_dir / "db" / db_name)
        else:
            db_path = str(Path(db_path) / db_name)
            
        with cls._instances_lock:
            if db_path not in cls._instances:
                instance = super(ExcelMetadataStorage, cls).__new__(cls)
                instance._initialized = False
                cls._instances[db_path] = instance
            return cls._instances[db_path]

    def __init__(self, db_path: str = None, db_name: str = "excel_metadata.db"):
        """Initialize the metadata storage."""
        if self._initialized:
            print("ExcelMetadataStorage already initialized")
            return

        if db_path is None:
            base_dir = Path(__file__).parent.parent
            db_dir = base_dir / "db"
            db_dir.mkdir(exist_ok=True, parents=True)
            self.db_path = str(db_dir / db_name)
        else:
            db_dir = Path(db_path)
            db_dir.mkdir(exist_ok=True, parents=True)
            self.db_path = str(db_dir / db_name)

        os.makedirs(os.path.dirname(os.path.abspath(Path(self.db_path))), exist_ok=True)
        print(f"ExcelMetadataStorage initialized with db_path: {self.db_path}")
        
        # Add thread lock for thread safety
        self._lock = threading.Lock()
        print("Thread lock added for thread safety")
        try:
            self.conn = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
                timeout=10.0,  # Reduced timeout
                isolation_level=None
            )
            print(f"SQLite connection established to {self.db_path}")
            
            # Set pragmas
            self.conn.execute("PRAGMA journal_mode=WAL")
            self.conn.execute("PRAGMA synchronous=NORMAL")
            self.conn.execute("PRAGMA cache_size=-2000")
            self.conn.execute("PRAGMA foreign_keys = ON")
            self.conn.row_factory = sqlite3.Row
            
            # Initialize schema
            self._init_schema_if_needed()
            print("Schema initialization complete")
            
            # Set up cleanup
            atexit.register(self.close)
            self._initialized = True
            print("ExcelMetadataStorage class completed initialization successfully with connection lock")

        except sqlite3.Error as e:
            print(f"Error initializing SQLite connection: {e}")
            if hasattr(self, 'conn') and self.conn:
                self.conn.close()

    def _init_schema_if_needed(self) -> None:
        """Initialize schema only if not already done for this database."""
        with self._lock:
            if self.db_path in _initialized_dbs:
                return
                
            cursor = self.conn.cursor()
            
            try:
                # First, check if tables exist
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='workbooks'
                """)
                table_exists = cursor.fetchone() is not None
                
                if not table_exists:
                    # If no tables exist, run the full schema initialization
                    self._init_schema()
                else:
                    # If tables exist, just ensure we have all the necessary tables
                    required_tables = {'workbooks', 'file_versions', 'chunks', 'cells', 'pending_edits'}
                    cursor.execute("""
                        SELECT name FROM sqlite_master 
                        WHERE type='table' AND name IN (?, ?, ?, ?, ?)
                    """, tuple(required_tables))
                    
                    existing_tables = {row[0] for row in cursor.fetchall()}
                    if required_tables - existing_tables:
                        # If any required tables are missing, recreate the schema
                        self._init_schema()
                
                # Create any missing indexes
                cursor.executescript("""
                    CREATE INDEX IF NOT EXISTS idx_chunks_version_id ON chunks(version_id);
                    CREATE INDEX IF NOT EXISTS idx_cells_version_sheet ON cells(version_id, sheet_name);
                    CREATE INDEX IF NOT EXISTS idx_file_versions_workbook ON file_versions(workbook_id);
                """)
                
                self.conn.commit()
                _initialized_dbs.add(self.db_path)
                print("ExcelMetadataStorage schema initialized and verified")
                
            except sqlite3.Error as e:
                self.conn.rollback()
                print(f"Error initializing schema: {e}")
                raise
            finally:
                cursor.close()

    def _init_schema(self) -> None:
        """Initialize the database schema."""
        print("Initializing ExcelMetadataStorage database schema...")
        cursor = self.conn.cursor()
        
        try:
            # Drop existing tables if they exist
            cursor.executescript("""
                PRAGMA foreign_keys = OFF;
                
                DROP TABLE IF EXISTS cells;
                DROP TABLE IF EXISTS chunks;
                DROP TABLE IF EXISTS file_versions;
                DROP TABLE IF EXISTS workbooks;
                
                PRAGMA foreign_keys = ON;
            """)
            
            # Create tables
            cursor.executescript("""
                -- Workbooks table
                CREATE TABLE workbooks (
                    workbook_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT NOT NULL UNIQUE,
                    file_name TEXT NOT NULL,
                    file_size INTEGER NOT NULL,
                    file_hash TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                -- File versions table
                CREATE TABLE file_versions (
                    version_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    workbook_id INTEGER NOT NULL,
                    version_number INTEGER NOT NULL,
                    change_description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    file_blob BLOB,
                    full_metadata_json TEXT,
                    FOREIGN KEY (workbook_id) REFERENCES workbooks(workbook_id) ON DELETE CASCADE,
                    UNIQUE(workbook_id, version_number)
                );
                
                -- Chunks table
                CREATE TABLE chunks (
                    chunk_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    version_id INTEGER NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    chunk_json TEXT NOT NULL,
                    chunk_text TEXT NOT NULL,
                    chunk_hash TEXT NOT NULL,
                    start_row INTEGER NOT NULL,
                    end_row INTEGER NOT NULL,
                    sheet_name TEXT NOT NULL,
                    is_modified BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (version_id) REFERENCES file_versions(version_id) ON DELETE CASCADE,
                    UNIQUE(version_id, chunk_index, sheet_name)
                );
                
                -- Cells table
                CREATE TABLE cells (
                    cell_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    version_id INTEGER NOT NULL,
                    chunk_id INTEGER NOT NULL,
                    sheet_name TEXT NOT NULL,
                    cell_address TEXT NOT NULL,
                    cell_json TEXT NOT NULL,
                    cell_hash TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (version_id) REFERENCES file_versions(version_id) ON DELETE CASCADE,
                    FOREIGN KEY (chunk_id) REFERENCES chunks(chunk_id) ON DELETE CASCADE,
                    UNIQUE(version_id, sheet_name, cell_address)
                );
                
                -- Pending edits table
                CREATE TABLE pending_edits (
                    edit_id TEXT PRIMARY KEY,
                    version_id INTEGER NOT NULL,
                    file_path TEXT NOT NULL,
                    sheet_name TEXT NOT NULL,
                    cell_address TEXT NOT NULL,
                    original_state TEXT NOT NULL,
                    cell_data TEXT NOT NULL,
                    intended_fill_color TEXT,
                    timestamp TEXT NOT NULL,
                    status TEXT DEFAULT 'pending'
                );
                
                -- Create indexes
                CREATE INDEX idx_chunks_version_id ON chunks(version_id);
                CREATE INDEX idx_cells_version_sheet ON cells(version_id, sheet_name);
                CREATE INDEX idx_file_versions_workbook ON file_versions(workbook_id);
                CREATE INDEX idx_pending_edits_version ON pending_edits(version_id);
                CREATE INDEX idx_pending_edits_status ON pending_edits(status);
                
                -- Set pragmas
                PRAGMA journal_mode=WAL;
                PRAGMA synchronous=NORMAL;
                PRAGMA cache_size=-2000;
                PRAGMA temp_store=MEMORY;
                PRAGMA mmap_size=30000000000;
                PRAGMA foreign_keys = ON;
            """)
            
            self.conn.commit()
            print("Database schema created successfully")
            
        except sqlite3.Error as e:
            self.conn.rollback()
            print(f"Error creating database schema: {e}")
            raise
        finally:
            cursor.close()
    
    def create_or_update_workbook(self, file_path: str) -> int:
        """Create or update a workbook entry."""
        with self._lock:
            cursor = self.conn.cursor()
            
            try:
                # Normalize file path
                normalized_path = str(Path(file_path).resolve())
                file_name = os.path.basename(normalized_path)
                
                # Calculate file hash if file exists
                file_hash = "empty"
                file_size = 0
                if os.path.exists(normalized_path):
                    file_hash = self._calculate_file_hash(normalized_path)
                    file_size = os.path.getsize(normalized_path)
                
                # Insert or update workbook
                cursor.execute("""
                    INSERT INTO workbooks (file_path, file_name, file_size, file_hash)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(file_path) DO UPDATE SET
                        file_size = excluded.file_size,
                        file_hash = excluded.file_hash,
                        updated_at = CURRENT_TIMESTAMP
                """, (normalized_path, file_name, file_size, file_hash))
                
                # Get the workbook_id
                cursor.execute("SELECT workbook_id FROM workbooks WHERE file_path = ?", (normalized_path,))
                result = cursor.fetchone()
                
                self.conn.commit()
                return result['workbook_id']
                
            except Exception as e:
                self.conn.rollback()
                raise
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate hash of file contents."""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.sha256(f.read()).hexdigest()
        except:
            return "error_reading_file"

    def create_new_version(
        self,
        file_path: str,
        change_description: str = None,
        full_metadata_json: str = None,
        chunks: List[Dict] = None,
    ) -> int:
        """
        Create a new version and optionally store full metadata and chunks.
        
        Args:
            file_path: Path to the Excel file
            change_description: Description of changes in this version
            full_metadata_json: Optional JSON string of full metadata
            chunks: Optional list of chunk dictionaries to store
            
        Returns:
            int: The new version ID
        """
        with self._lock:
            cursor = self.conn.cursor()
            
            try:
                cursor.execute("BEGIN TRANSACTION")
                
                # Normalize file path
                normalized_path = str(Path(file_path).resolve())
                
                # Ensure workbook exists
                cursor.execute("SELECT workbook_id FROM workbooks WHERE file_path = ?", (normalized_path,))
                file_row = cursor.fetchone()
                
                if not file_row:
                    # Create workbook entry if it doesn't exist
                    workbook_id = self.create_or_update_workbook(normalized_path)
                else:
                    workbook_id = file_row['workbook_id']
                
                # Get latest version number
                cursor.execute("""
                    SELECT COALESCE(MAX(version_number), 0) + 1 as next_version
                    FROM file_versions 
                    WHERE workbook_id = ?
                """, (workbook_id,))
                version_number = cursor.fetchone()['next_version']
                
                # Get previous version ID
                cursor.execute("""
                    SELECT version_id 
                    FROM file_versions 
                    WHERE workbook_id = ? 
                    ORDER BY version_number DESC 
                    LIMIT 1
                """, (workbook_id,))
                prev_version = cursor.fetchone()
                prev_version_id = prev_version['version_id'] if prev_version else None
                
                # Create new version record
                if prev_version_id:
                    # Copy from previous version
                    cursor.execute("""
                        INSERT INTO file_versions (
                            workbook_id, version_number, change_description, 
                            file_blob, full_metadata_json
                        ) 
                        SELECT 
                            workbook_id, 
                            ? as version_number, 
                            ? as change_description,
                            file_blob,
                            full_metadata_json
                        FROM file_versions
                        WHERE workbook_id = ? AND version_id = ?
                    """, (version_number, change_description or f"Version {version_number}", 
                          workbook_id, prev_version_id))
                else:
                    # First version - create new
                    cursor.execute("""
                        INSERT INTO file_versions (
                            workbook_id, 
                            version_number, 
                            change_description,
                            full_metadata_json,
                            created_at,
                            updated_at
                        ) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """, (
                        workbook_id, 
                        version_number, 
                        change_description or "Initial version",
                        full_metadata_json or '' # store the full metadata_json from the args
                    ))
                
                new_version_id = cursor.lastrowid
                
                if prev_version_id:
                    # Copy chunks and cells from previous version
                    cursor.execute("""
                        INSERT INTO chunks (
                            version_id, chunk_index, chunk_json, chunk_text, 
                            chunk_hash, start_row, end_row, sheet_name, is_modified
                        )
                        SELECT 
                            ? as version_id, 
                            chunk_index, 
                            chunk_json, 
                            chunk_text,
                            chunk_hash,
                            start_row,
                            end_row,
                            sheet_name,
                            0 as is_modified
                        FROM chunks
                        WHERE version_id = ?
                    """, (new_version_id, prev_version_id))
                    
                    # Copy cells
                    cursor.execute("""
                        INSERT INTO cells (
                            version_id, chunk_id, sheet_name, cell_address, 
                            cell_json, cell_hash
                        )
                        SELECT 
                            ? as version_id,
                            (SELECT c2.chunk_id 
                             FROM chunks c2 
                             WHERE c2.version_id = ? 
                               AND c2.chunk_index = c1.chunk_index
                               AND c2.sheet_name = c1.sheet_name
                               AND c2.start_row = c1.start_row
                               AND c2.end_row = c1.end_row
                            ) as chunk_id,
                            cl.sheet_name,
                            cl.cell_address,
                            cl.cell_json,
                            cl.cell_hash
                        FROM cells cl
                        JOIN chunks c1 ON cl.chunk_id = c1.chunk_id
                        WHERE cl.version_id = ?
                    """, (new_version_id, new_version_id, prev_version_id))

                else:
                    # Store chunks if provided
                    if chunks and isinstance(chunks, list):
                        for chunk_idx, chunk in enumerate(chunks):
                            if not isinstance(chunk, dict):
                                continue
                                
                            # Extract chunk data
                            chunk_json = json.dumps(chunk)
                            chunk_text = self._generate_chunk_text(chunk)
                            chunk_hash = self._calculate_hash(chunk_json)
                            
                            # Store chunk
                            cursor.execute("""
                                INSERT INTO chunks (
                                    version_id, 
                                    chunk_index, 
                                    chunk_json, 
                                    chunk_text,
                                    chunk_hash,
                                    sheet_name,
                                    start_row,
                                    end_row,
                                    is_modified,
                                    created_at,
                                    updated_at
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                            """, (
                                new_version_id,
                                chunk_idx,
                                chunk_json,
                                chunk_text,
                                chunk_hash,
                                chunk.get('sheetName', ''),
                                chunk.get('startRow', 0),
                                chunk.get('endRow', 0)
                            ))
                            
                            chunk_id = cursor.lastrowid

                            # Store cells if present in chunk
                            if 'cellData' in chunk and isinstance(chunk['cellData'], list):
                                for row_idx, row in enumerate(chunk['cellData']):
                                    if not isinstance(row, list):
                                        continue
                                        
                                    for col_idx, cell in enumerate(row):
                                        if not isinstance(cell, dict):
                                            continue
                                            
                                        cell_address = cell.get('address') or f"{chr(65 + col_idx)}{row_idx + 1}"
                                        cell_json = json.dumps(cell)
                                        cell_hash = self._calculate_hash(cell_json)
                                        
                                        cursor.execute("""
                                            INSERT INTO cells (
                                                version_id,
                                                chunk_id,
                                                sheet_name,
                                                cell_address,
                                                cell_json,
                                                cell_hash,
                                                created_at,
                                                updated_at
                                            ) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                                        """, (
                                            new_version_id,
                                            chunk_id,
                                            chunk.get('sheetName', ''),
                                            cell_address,
                                            cell_json,
                                            cell_hash
                                        ))  
                        
                self.conn.commit()
                return new_version_id
                
            except Exception as e:
                self.conn.rollback()
                raise

    def store_file_blob(self, file_path: str, version_id: Optional[int] = None, overwrite: bool = False) -> bool:
        """
        Store the Excel file as a blob, with automatic version management.
        
        Args:
            file_path: Path to the Excel file
            version_id: Optional version ID. If None, will auto-increment from latest version.
            overwrite: If True and version_id is None, overwrite latest version. 
                     If False and version_id is None, create new version.
                     If version_id is provided, overwrite that specific version.
            
        Returns:
            bool: True if blob was stored or already exists, False on error
        """
        try:
            normalized_path = str(Path(file_path).resolve())
            
            with self._lock:
                cursor = self.conn.cursor()
                
                # If version_id is not provided, find the latest version for this file
                if version_id is None:
                    cursor.execute("""
                        SELECT v.version_id, v.file_blob
                        FROM file_versions v
                        JOIN workbooks w ON v.workbook_id = w.workbook_id
                        WHERE w.file_path = ?
                        ORDER BY v.version_id DESC
                        LIMIT 1
                    """, (normalized_path,))
                    
                    latest = cursor.fetchone()
                    
                    if latest and latest['file_blob'] is not None and not overwrite:
                        # Create new version
                        new_version_id = self.create_new_version(
                            file_path=normalized_path,
                            change_description=f"New version created at {datetime.now().isoformat()}"
                        )
                        version_id = new_version_id
                    elif latest:
                        # Use existing version (overwrite or no blob exists yet)
                        version_id = latest['version_id']
                    else:
                        # First version of this file
                        self.create_or_update_workbook(normalized_path)
                        version_id = 1
                
                # If version_id was provided, check if we can overwrite
                elif not overwrite:
                    cursor.execute("""
                        SELECT file_blob 
                        FROM file_versions 
                        WHERE version_id = ? AND file_blob IS NOT NULL
                    """, (version_id,))
                    
                    if cursor.fetchone():
                        # Blob exists and we're not overwriting
                        return True
            
            # Read the file
            with open(file_path, 'rb') as f:
                file_blob = f.read()
            
            # Ensure the workbook and version exist in the database
            with self._lock:
                cursor = self.conn.cursor()
                
                # Verify the version exists or create it
                cursor.execute("""
                    SELECT 1 FROM file_versions WHERE version_id = ?
                """, (version_id,))
                
                if not cursor.fetchone():
                    # Version doesn't exist, create it
                    self.create_or_update_workbook(normalized_path)
                    cursor.execute("""
                        INSERT INTO file_versions (workbook_id, version_id, change_description, created_at, updated_at)
                        SELECT w.workbook_id, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                        FROM workbooks w
                        WHERE w.file_path = ?
                    """, (version_id, f"Initial version {version_id}", normalized_path))
                
                # Update the blob
                cursor.execute("""
                    UPDATE file_versions
                    SET file_blob = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE version_id = ?
                """, (sqlite3.Binary(file_blob), version_id))
                
                self.conn.commit()
                return True
                
        except Exception as e:
            self.conn.rollback()
            print(f"Error storing file blob: {e}")
            return False


    def get_file_blob(self, file_path: str, version_id: int) -> Optional[bytes]:
        """
        Retrieve the stored Excel file blob for a specific file and version.
        
        Args:
            file_path: Path to the Excel file
            version_id: The version ID to retrieve
            
        Returns:
            bytes: The file blob if found, None otherwise
        """
        normalized_path = str(Path(file_path).resolve())
        with self._lock:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT v.file_blob 
                FROM file_versions v
                JOIN workbooks w ON v.workbook_id = w.workbook_id
                WHERE w.file_path = ? AND v.version_id = ?
            """, (normalized_path, version_id))
            
            result = cursor.fetchone()
            return result['file_blob'] if result and result['file_blob'] else None

    def save_blob_to_file(self, file_path: str, version_id: int, output_path: str) -> bool:
        """
        Save a stored blob back to a file.
        
        Args:
            file_path: Path to the source Excel file
            version_id: The version ID to retrieve
            output_path: Path where to save the file
            
        Returns:
            bool: True if the file was saved successfully, False otherwise
        """
        blob = self.get_file_blob(file_path, version_id)
        if not blob:
            return False
            
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'wb') as f:
                f.write(blob)
            return True
        except Exception as e:
            print(f"Error saving blob to file: {e}")
            return False

    def _parse_cell_address(self, address: str) -> tuple:
        """Parse cell address into column letters and row number."""
        match = re.match(r'^([A-Z]+)(\d+)$', address.upper())
        if not match:
            raise ValueError(f"Invalid cell address: {address}")
        return match.group(1), int(match.group(2))
    
    def _column_to_number(self, column: str) -> int:
        """Convert column letters to number (A=1, B=2, ..., Z=26, AA=27, etc.)"""
        result = 0
        for char in column:
            result = result * 26 + (ord(char) - ord('A') + 1)
        return result

    def update_cells(
        self,
        version_id: int,
        cell_updates: List[Dict[str, Any]],
        file_path: Optional[str] = None
    ) -> bool:
        """
        Update multiple cells in the specified version.
        
        Args:
            version_id: The version ID to update
            cell_updates: List of cell updates, each containing:
                - sheet_name: Name of the sheet
                - cell_address: Address of the cell (e.g., 'A1')
                - cell_data: Dictionary containing cell data (value, formatting, etc.)
            file_path: Optional path to the workbook file (for validation)
            
        Returns:
            bool: True if all updates were successful, False otherwise
        """
        if not cell_updates:
            return True
            
        with self._lock:
            cursor = self.conn.cursor()
            
            try:
                cursor.execute("BEGIN TRANSACTION")
                
                # Verify the version exists and get workbook info
                cursor.execute("""
                    SELECT v.workbook_id, w.file_path
                    FROM file_versions v
                    JOIN workbooks w ON v.workbook_id = w.workbook_id
                    WHERE v.version_id = ?
                """, (version_id,))
                
                version_info = cursor.fetchone()
                if not version_info:
                    logger.error(f"Version {version_id} not found")
                    return False
                    
                # If file_path was provided, verify it matches
                if file_path and str(Path(file_path).resolve()) != version_info['file_path']:
                    logger.error(f"File path mismatch for version {version_id}")
                    return False
                    
                # Process each cell update
                for update in cell_updates:
                    sheet_name = update.get('sheet_name')
                    cell_address = update.get('cell_address')
                    cell_data = update.get('cell_data', {})
                    
                    if not all([sheet_name, cell_address, cell_data]):
                        logger.warning(f"Skipping invalid cell update: {update}")
                        continue
                        
                    # Find the chunk containing this cell
                    cursor.execute("""
                        SELECT c.chunk_id, c.chunk_json
                        FROM chunks c
                        WHERE c.version_id = ? 
                        AND c.sheet_name = ?
                        AND c.start_row <= ?
                        AND c.end_row >= ?
                    """, (
                        version_id,
                        sheet_name,
                        int(re.search(r'\d+', cell_address).group()),  # Extract row number
                        int(re.search(r'\d+', cell_address).group())
                    ))
                    
                    chunk = cursor.fetchone()
                    if not chunk:
                        logger.warning(f"No chunk found for cell {sheet_name}!{cell_address}")
                        continue
                        
                    # Parse chunk data
                    chunk_data = json.loads(chunk['chunk_json'])
                    cell_found = False
                    
                    # Update cell in chunk data
                    for row in chunk_data.get('cellData', []):
                        for cell in row:
                            if cell.get('address') == cell_address:
                                # Update cell data
                                cell.update(cell_data)
                                cell_found = True
                                break
                        if cell_found:
                            break
                            
                    if not cell_found:
                        logger.warning(f"Cell {sheet_name}!{cell_address} not found in chunk")
                        continue
                        
                    # Update chunk in database
                    chunk_json = json.dumps(chunk_data)
                    chunk_text = self._generate_chunk_text(chunk_data)
                    chunk_hash = self._calculate_hash(chunk_json)
                    
                    cursor.execute("""
                        UPDATE chunks
                        SET chunk_json = ?,
                            chunk_text = ?,
                            chunk_hash = ?,
                            is_modified = 1,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE chunk_id = ?
                    """, (
                        chunk_json,
                        chunk_text,
                        chunk_hash,
                        chunk['chunk_id']
                    ))
                    
                    # Update cell in cells table
                    cell_json = json.dumps(cell_data)
                    cell_hash = self._calculate_hash(cell_json)
                    
                    cursor.execute("""
                        INSERT OR REPLACE INTO cells (
                            version_id,
                            chunk_id,
                            sheet_name,
                            cell_address,
                            cell_json,
                            cell_hash,
                            created_at,
                            updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """, (
                        version_id,
                        chunk['chunk_id'],
                        sheet_name,
                        cell_address,
                        cell_json,
                        cell_hash
                    ))
                
                # Update the full metadata for the version
                self._update_full_metadata(cursor, version_id)
                
                self.conn.commit()
                return True
                
            except Exception as e:
                self.conn.rollback()
                logger.error(f"Error updating cells: {e}")
                return False
    
    def _update_chunk_from_cells(self, cursor, version_id: int, chunk_id: int) -> None:
        """Update a chunk's metadata based on its cells."""
        # Get all cells in this chunk
        cursor.execute("""
            SELECT cell_address, cell_json 
            FROM cells 
            WHERE version_id = ? AND chunk_id = ?
        """, (version_id, chunk_id))
        
        cells = []
        for row in cursor.fetchall():
            cell_data = json.loads(row['cell_json'])
            cell_data['address'] = row['cell_address']
            cells.append(cell_data)
        
        if not cells:
            return
        
        # Sort cells properly
        cells.sort(key=lambda c: (
            self._parse_cell_address(c['address'])[1],  # Row number
            self._column_to_number(self._parse_cell_address(c['address'])[0])  # Column number
        ))
        
        # Get chunk metadata
        chunk_metadata = self._get_chunk_metadata(cursor, version_id, chunk_id)
        
        # Reconstruct chunk data
        chunk_data = {
            'chunkId': f"chunk_{chunk_id}",
            'cellData': self._organize_cells_into_rows(cells),
            **chunk_metadata
        }
        
        # Update chunk
        chunk_text = self._generate_chunk_text(chunk_data)
        chunk_json = json.dumps(chunk_data)
        chunk_hash = self._calculate_hash(chunk_json)
        
        cursor.execute("""
            UPDATE chunks
            SET chunk_json = ?,
                chunk_text = ?,
                chunk_hash = ?,
                is_modified = 1,
                updated_at = CURRENT_TIMESTAMP
            WHERE chunk_id = ?
        """, (chunk_json, chunk_text, chunk_hash, chunk_id))

    def _organize_cells_into_rows(self, cells: List[dict]) -> List[List[dict]]:
        """Organize flat list of cells into rows based on their addresses."""
        rows = {}
        
        for cell in cells:
            try:
                _, row_num = self._parse_cell_address(cell['address'])
                if row_num not in rows:
                    rows[row_num] = []
                rows[row_num].append(cell)
            except ValueError:
                print(f"Warning: Skipping cell with invalid address: {cell.get('address', 'unknown')}")
                continue
        
        # Sort rows and cells within rows
        sorted_rows = []
        for row_num in sorted(rows.keys()):
            sorted_cells = sorted(rows[row_num], 
                                key=lambda c: self._column_to_number(
                                    self._parse_cell_address(c['address'])[0]
                                ))
            sorted_rows.append(sorted_cells)
        
        return sorted_rows

    def _get_chunk_metadata(self, cursor, version_id: int, chunk_id: int) -> dict:
        """Get the base metadata for a chunk."""
        cursor.execute("""
            SELECT chunk_json 
            FROM chunks 
            WHERE version_id = ? AND chunk_id = ?
        """, (version_id, chunk_id))
        
        result = cursor.fetchone()
        if not result:
            raise ValueError(f"Chunk {chunk_id} not found in version {version_id}")
            
        chunk_data = json.loads(result['chunk_json'])
        
        # Return only the metadata, not the cell data
        return {k: v for k, v in chunk_data.items() if k != 'cellData'}

    def _update_full_metadata(self, cursor, version_id: int) -> None:
        """Update the full metadata JSON for a version."""
        # Get all chunks for this version
        cursor.execute("""
            SELECT chunk_json 
            FROM chunks 
            WHERE version_id = ?
            ORDER BY sheet_name, chunk_index
        """, (version_id,))
        
        chunks = [json.loads(row['chunk_json']) for row in cursor.fetchall()]
        if not chunks:
            return
        
        # Get workbook info
        cursor.execute("""
            SELECT w.file_name, w.file_path
            FROM file_versions v
            JOIN workbooks w ON v.workbook_id = w.workbook_id
            WHERE v.version_id = ?
        """, (version_id,))
        
        workbook_info = cursor.fetchone()
        
        # Reconstruct full metadata
        full_metadata = {
            'workbookName': workbook_info['file_name'] if workbook_info else '',
            'workbookPath': workbook_info['file_path'] if workbook_info else '',
            'versionId': version_id,
            'extractedAt': datetime.now().isoformat(),
            'totalChunks': len(chunks),
            'chunks': chunks
        }
        
        # Update the version record
        cursor.execute("""
            UPDATE file_versions
            SET full_metadata_json = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE version_id = ?
        """, (json.dumps(full_metadata), version_id))

    def _generate_chunk_text(self, chunk_data: dict) -> str:
        """Generate text representation of chunk for embedding."""
        text_parts = []
        
        # Add sheet name
        if 'sheetName' in chunk_data:
            text_parts.append(f"Sheet: {chunk_data['sheetName']}")
        
        # Add cell values
        for row in chunk_data.get('cellData', []):
            row_text = []
            for cell in row:
                value = cell.get('value', '')
                if value:
                    row_text.append(str(value))
            if row_text:
                text_parts.append(' | '.join(row_text))
        
        return '\n'.join(text_parts)

    def _calculate_hash(self, content: str) -> str:
        """Calculate SHA-256 hash of content."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    # Query methods
    def get_chunk(self, version_id: int, chunk_id: int = None, 
                  sheet_name: str = None, row: int = None) -> Optional[dict]:
        """Get a specific chunk by ID or by sheet/row."""
        with self._lock:
            cursor = self.conn.cursor()
            
            query = """
                SELECT chunk_json 
                FROM chunks 
                WHERE version_id = ?
            """
            params = [version_id]
            
            if chunk_id:
                query += " AND chunk_id = ?"
                params.append(chunk_id)
            elif sheet_name is not None and row is not None:
                query += " AND sheet_name = ? AND start_row <= ? AND end_row >= ?"
                params.extend([sheet_name, row, row])
            else:
                return None
                
            cursor.execute(query, params)
            result = cursor.fetchone()
            return json.loads(result['chunk_json']) if result else None

    def get_cell(self, version_id: int, sheet_name: str, cell_address: str) -> Optional[dict]:
        """Get a specific cell's metadata."""
        with self._lock:
            cursor = self.conn.cursor()
            
            cursor.execute("""
                SELECT cell_json 
                FROM cells 
                WHERE version_id = ? AND sheet_name = ? AND cell_address = ?
            """, (version_id, sheet_name, cell_address))
            
            result = cursor.fetchone()
            return json.loads(result['cell_json']) if result else None


    def get_workbook_id(self, file_path: str) -> Optional[int]:
        """Get the workbook ID for a given file path."""
        with self._lock:
            cursor = self.conn.cursor()
            normalized_path = str(Path(file_path).resolve())
            cursor.execute("""
                SELECT workbook_id 
                FROM workbooks 
                WHERE file_path = ?
            """, (normalized_path,))
            result = cursor.fetchone()
            return result['workbook_id'] if result else None

    def get_latest_version(self, file_path: str) -> Optional[dict]:
        """Get the latest version of a workbook by file path."""
        with self._lock:
            cursor = self.conn.cursor()
            normalized_path = str(Path(file_path).resolve())
            
            # Get the latest version in a single query
            cursor.execute("""
                SELECT v.* 
                FROM file_versions v
                JOIN workbooks w ON v.workbook_id = w.workbook_id
                WHERE w.file_path = ?
                ORDER BY v.version_number DESC
                LIMIT 1
            """, (normalized_path,))
            
            result = cursor.fetchone()
            if not result:
                return None
                
            # Convert to dict for easier use
            return dict(result)

    def get_latest_metadata(self, file_path: str) -> Optional[dict]:
        """Get the full metadata of the latest version of a workbook."""
        latest_version = self.get_latest_version(file_path)
        if not latest_version:
            return None
            
        return self.get_workbook_metadata(latest_version['version_id'])

    def get_workbook_metadata(self, version_id: int) -> dict:
        """Get full workbook metadata for a version."""
        with self._lock:
            cursor = self.conn.cursor()
            
            cursor.execute("""
                SELECT full_metadata_json 
                FROM file_versions 
                WHERE version_id = ?
            """, (version_id,))
            
            result = cursor.fetchone()
            if not result or not result['full_metadata_json']:
                return None
                
            return json.loads(result['full_metadata_json'])

    def get_all_chunks(self, version_id: int, sheet_name: str = None) -> List[dict]:
        """Get all chunks for a version, optionally filtered by sheet."""
        try:
            with self._lock:
                cursor = self.conn.cursor()
                
                query = """
                    SELECT chunk_id, chunk_json, sheet_name, start_row, end_row
                    FROM chunks 
                    WHERE version_id = ?
                """
                params = [version_id]
                
                if sheet_name:
                    query += " AND sheet_name = ?"
                    params.append(sheet_name)
                    
                query += " ORDER BY sheet_name, chunk_index"
                
                cursor.execute(query, params)
                
                results = []
                for row in cursor.fetchall():
                    chunk_data = json.loads(row['chunk_json'])
                    chunk_data['_metadata'] = {
                        'chunk_id': row['chunk_id'],
                        'sheet_name': row['sheet_name'],
                        'start_row': row['start_row'],
                        'end_row': row['end_row']
                    }
                    results.append(chunk_data)
                    
                return results
            
        except (sqlite3.Error, json.JSONDecodeError) as e:
            print(f"Error getting chunks: {e}")
            return []
    
    # Pending Edits Management Methods--------------------------------------------------------------------------------------------------------
    
    def _ensure_pending_edits_table(self) -> None:
        """Ensure the pending_edits table exists."""
        with self._lock:
            cursor = self.conn.cursor()
            try:
                # Create table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS pending_edits (
                        edit_id TEXT PRIMARY KEY,
                        version_id INTEGER NOT NULL,
                        file_path TEXT NOT NULL,
                        sheet_name TEXT NOT NULL,
                        cell_address TEXT NOT NULL,
                        original_state TEXT NOT NULL,
                        cell_data TEXT NOT NULL,
                        intended_fill_color TEXT,
                        timestamp TEXT NOT NULL,
                        status TEXT DEFAULT 'pending'
                    )
                """)
                
                # Create index 1
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_pending_edits_version 
                    ON pending_edits(version_id)
                """)
                
                # Create index 2
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_pending_edits_status 
                    ON pending_edits(status)
                """)
                
                self.conn.commit()
                logger.info("Called _ensure_pending_edits method and verified pending_edits table and indexes exist")
            except sqlite3.Error as e:
                self.conn.rollback()
                logger.error(f"Error ensuring pending_edits table: {e}")
                raise
            finally:
                cursor.close()
        
    
    def create_pending_edit(self, **kwargs) -> str:
        """
        Create a new pending edit record.
        
        Args:
            **kwargs: Should contain:
                - edit_id: Unique ID for the edit
                - version_id: Version ID this edit belongs to
                - file_path: Path to the workbook file
                - sheet_name: Name of the sheet
                - cell_address: Address of the cell being edited
                - original_state: Dict containing original cell state
                - cell_data: Dict containing new cell data
                - intended_fill_color: Optional fill color for the cell
                
        Returns:
            str: The edit_id if successful, None otherwise
        """
        required_fields = ['edit_id', 'version_id', 'file_path', 'sheet_name', 
                         'cell_address', 'original_state', 'cell_data']
        
        if not all(field in kwargs for field in required_fields):
            raise ValueError(f"Missing required fields. Required: {required_fields}")
        
        try:
            edit_data = {
                'edit_id': kwargs['edit_id'],
                'version_id': kwargs['version_id'],
                'file_path': kwargs['file_path'],
                'sheet_name': kwargs['sheet_name'],
                'cell_address': kwargs['cell_address'],
                'original_state': json.dumps(kwargs['original_state']),
                'cell_data': json.dumps(kwargs['cell_data']),
                'intended_fill_color': kwargs.get('intended_fill_color'),
                'timestamp': kwargs.get('timestamp', datetime.utcnow().isoformat()),
                'status': 'pending'
            }
            
            with self._lock:
                cursor = self.conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO pending_edits 
                    (edit_id, version_id, file_path, sheet_name, cell_address, 
                     original_state, cell_data, intended_fill_color, timestamp, status)
                    VALUES 
                    (:edit_id, :version_id, :file_path, :sheet_name, :cell_address,
                     :original_state, :cell_data, :intended_fill_color, :timestamp, :status)
                ''', edit_data)
                
                self.conn.commit()
                return edit_data['edit_id']
                
        except sqlite3.Error as e:
            self.conn.rollback()
            print(f"Error creating pending edit: {e}")
            raise
    
    def get_pending_edit(self, edit_id: str) -> Optional[Dict]:
        """
        Retrieve a pending edit by its ID.
        
        Args:
            edit_id: The ID of the edit to retrieve
            
        Returns:
            Dict containing the edit data, or None if not found
        """
        try:
            with self._lock:
                cursor = self.conn.cursor()
                cursor.execute('''
                    SELECT * FROM pending_edits 
                    WHERE edit_id = ?
                ''', (edit_id,))
                
                row = cursor.fetchone()
                if not row:
                    return None
                
                # Convert to dict and deserialize JSON fields
                edit = dict(row)
                edit['original_state'] = json.loads(edit['original_state'])
                edit['cell_data'] = json.loads(edit['cell_data'])
                return edit
                
        except (sqlite3.Error, json.JSONDecodeError) as e:
            print(f"Error getting pending edit: {e}")
            return None
    
    def get_pending_edits_for_version(self, version_id: int, 
                                     sheet_name: str = None, 
                                     status: str = 'pending') -> List[Dict]:
        """
        Retrieve all pending edits for a specific version and optional sheet.
        
        Args:
            version_id: The version ID to get edits for
            sheet_name: Optional sheet name to filter by
            status: Status filter ('pending', 'accepted', 'rejected')
            
        Returns:
            List of edit dictionaries
        """
        try:
            query = '''
                SELECT * FROM pending_edits 
                WHERE version_id = ? AND status = ?
            '''
            params = [version_id, status]
            
            if sheet_name:
                query += ' AND sheet_name = ?'
                params.append(sheet_name)
                
            query += ' ORDER BY timestamp DESC'
            
            with self._lock:
                cursor = self.conn.cursor()
                cursor.execute(query, params)
                
                edits = []
                for row in cursor.fetchall():
                    edit = dict(row)
                    edit['original_state'] = json.loads(edit['original_state'])
                    edit['cell_data'] = json.loads(edit['cell_data'])
                    edits.append(edit)
                    
                return edits
                
        except (sqlite3.Error, json.JSONDecodeError) as e:
            print(f"Error getting pending edits: {e}")
            return []
    
    def update_edit_status(self, edit_id: str, status: str) -> bool:
        """
        Update the status of an edit.
        
        Args:
            edit_id: The ID of the edit to update
            status: New status ('pending', 'accepted', 'rejected')
            
        Returns:
            bool: True if update was successful, False otherwise
        """
        if status not in ('pending', 'accepted', 'rejected'):
            raise ValueError("Status must be one of: 'pending', 'accepted', 'rejected'")
            
        try:
            with self._lock:
                cursor = self.conn.cursor()
                cursor.execute('''
                    UPDATE pending_edits 
                    SET status = ?, timestamp = ?
                    WHERE edit_id = ?
                ''', (status, datetime.utcnow().isoformat(), edit_id))
                
                self.conn.commit()
                return cursor.rowcount > 0
                
        except sqlite3.Error as e:
            self.conn.rollback()
            print(f"Error updating edit status: {e}")
            return False
    
    def delete_pending_edit(self, edit_id: str) -> bool:
        """
        Delete a pending edit.
        
        Args:
            edit_id: The ID of the edit to delete
            
        Returns:
            bool: True if deletion was successful, False otherwise
        """
        try:
            with self._lock:
                cursor = self.conn.cursor()
                cursor.execute('''
                    DELETE FROM pending_edits 
                    WHERE edit_id = ?
                ''', (edit_id,))
                
                self.conn.commit()
                return cursor.rowcount > 0
                
        except sqlite3.Error as e:
            self.conn.rollback()
            print(f"Error deleting pending edit: {e}")
            return False
    
    def get_pending_edits_by_ids(self, edit_ids: List[str]) -> List[Dict]:
        """
        Get multiple pending edits by their IDs.
        
        Args:
            edit_ids: List of edit IDs to retrieve
            
        Returns:
            List of edit dictionaries, in the same order as the input IDs.
            If an edit is not found, it will be omitted from the results.
        """
        if not edit_ids:
            return []
            
        try:
            with self._lock:
                # Create a parameterized query with the right number of placeholders
                placeholders = ','.join('?' * len(edit_ids))
                query = f'''
                    SELECT * FROM pending_edits 
                    WHERE edit_id IN ({placeholders})
                '''
                
                cursor = self.conn.cursor()
                cursor.execute(query, edit_ids)
                
                # Create a dict of edit_id -> edit for quick lookup
                edits_by_id = {}
                for row in cursor.fetchall():
                    edit = dict(row)
                    # Deserialize JSON fields
                    edit['original_state'] = json.loads(edit['original_state'])
                    edit['cell_data'] = json.loads(edit['cell_data'])
                    edits_by_id[edit['edit_id']] = edit
                
                # Return results in the order of input IDs, skipping any not found
                return [edits_by_id[edit_id] for edit_id in edit_ids if edit_id in edits_by_id]
                
        except (sqlite3.Error, json.JSONDecodeError) as e:
            print(f"Error getting batch pending edits: {e}")
            return []
    
    def delete_pending_edits(self, edit_ids: List[str]) -> int:
        """
        Delete multiple pending edits by their IDs.
        
        Args:
            edit_ids: List of edit IDs to delete
            
        Returns:
            int: Number of edits successfully deleted
        """
        if not edit_ids:
            return 0
            
        try:
            with self._lock:
                cursor = self.conn.cursor()
                
                # Create a temporary table for batch delete
                cursor.execute('CREATE TEMP TABLE IF NOT EXISTS temp_edit_ids (edit_id TEXT PRIMARY KEY)')
                
                # Insert the IDs to delete
                cursor.executemany(
                    'INSERT OR IGNORE INTO temp_edit_ids (edit_id) VALUES (?)',
                    [(edit_id,) for edit_id in edit_ids]
                )
                
                # Perform the delete using a join with the temp table
                cursor.execute('''
                    DELETE FROM pending_edits
                    WHERE edit_id IN (SELECT edit_id FROM temp_edit_ids)
                ''')
                
                # Clean up
                cursor.execute('DROP TABLE IF EXISTS temp_edit_ids')
                
                count = cursor.rowcount
                self.conn.commit()
                return count
                
        except sqlite3.Error as e:
            self.conn.rollback()
            print(f"Error deleting batch pending edits: {e}")
            return 0
    
    def cleanup_old_edits(self, days_old: int = 30) -> int:
        """
        Remove edits older than the specified number of days.
        
        Args:
            days_old: Remove edits older than this many days
            
        Returns:
            int: Number of edits removed
        """
        try:
            cutoff_date = (datetime.utcnow() - timedelta(days=days_old)).isoformat()
            
            with self._lock:
                cursor = self.conn.cursor()
                cursor.execute('''
                    DELETE FROM pending_edits 
                    WHERE timestamp < ?
                ''', (cutoff_date,))
                
                count = cursor.rowcount
                self.conn.commit()
                return count
                
        except sqlite3.Error as e:
            self.conn.rollback()
            print(f"Error cleaning up old edits: {e}")
            return 0
    
    
    def batch_update_edit_statuses(self, edit_ids: List[str], new_status: str) -> Dict[str, Any]:
        """
        Batch update edit statuses and return full edit data.
        
        Args:
            edit_ids: List of edit IDs to update
            new_status: New status ('accepted' or 'rejected')
            
        Returns:
            Dict containing:
                - 'updated_count': Number of successfully updated edits
                - 'failed_ids': List of edit IDs that failed to update
                - 'edits': List of full edit data for successfully updated edits
                - 'original_states': Dict mapping edit IDs to original cell states
        """
        if not edit_ids:
            return {
                'updated_count': 0,
                'failed_ids': [],
                'edits': [],
                'original_states': {}
            }
        
        try:
            with self._lock:
                cursor = self.conn.cursor()
                
                # Create temp table for batch operations
                cursor.execute('''
                    CREATE TEMP TABLE IF NOT EXISTS temp_edits (
                        edit_id TEXT PRIMARY KEY,
                        status TEXT,
                        timestamp TEXT
                    )
                ''')
                
                # Insert into temp table
                now = datetime.utcnow().isoformat()
                cursor.executemany(
                    'INSERT OR REPLACE INTO temp_edits (edit_id, status, timestamp) VALUES (?, ?, ?)',
                    [(edit_id, new_status, now) for edit_id in edit_ids]
                )
                
                # Get full edit data before updating
                cursor.execute('''
                    SELECT pe.*, te.status as new_status
                    FROM pending_edits pe
                    JOIN temp_edits te ON pe.edit_id = te.edit_id
                ''')
                
                # Store full edit data and original states
                edits = []
                original_states = {}
                failed_ids = set(edit_ids)
                
                for row in cursor.fetchall():
                    edit = dict(zip([col[0] for col in cursor.description], row))
                    edit_id = edit['edit_id']
                    original_states[edit_id] = json.loads(edit['original_state'])
                    edits.append(edit)
                    failed_ids.remove(edit_id)
                
                # Update statuses in main table
                cursor.execute('''
                    UPDATE pending_edits
                    SET status = te.status,
                        timestamp = te.timestamp
                    FROM temp_edits te
                    WHERE pending_edits.edit_id = te.edit_id
                ''')
                
                # Clean up
                cursor.execute('DROP TABLE IF EXISTS temp_edits')
                self.conn.commit()
                
                return {
                    'updated_count': len(edits),
                    'failed_ids': list(failed_ids),
                    'edits': edits,
                    'original_states': original_states
                }
                
        except (sqlite3.Error, json.JSONDecodeError) as e:
            self.conn.rollback()
            print(f"Error batch updating edit statuses: {e}")
            return {
                'updated_count': 0,
                'failed_ids': edit_ids,
                'edits': [],
                'original_states': {}
            }

    
    def batch_create_pending_edits(self, edits: List[Dict]) -> List[str]:
        """
        Batch create multiple pending edits in a single transaction.
        
        Args:
            edits: List of edit dictionaries, each containing:
                - edit_id: Unique ID for the edit
                - version_id: Version ID this edit belongs to
                - file_path: Path to the workbook
                - sheet_name: Name of the sheet
                - cell_address: Address of the cell being edited
                - original_state: Dict containing original cell state
                - cell_data: Dict containing new cell data
                - intended_fill_color: Optional fill color for the cell
                
        Returns:
            List of edit_ids that were successfully created
        """
        if not edits:
            return []


        # Ensure pending edits table exists
        try: 
            self._ensure_pending_edits_table()
        except sqlite3.Error as e:
            logger.error(f"Failed to ensure pending_edits table: {e}")
            raise
            
        try:
            with self._lock:
                cursor = self.conn.cursor()
                now = datetime.utcnow().isoformat()
                
                # Prepare batch data
                batch_data = []
                for edit in edits:
                    batch_data.append((
                        edit['edit_id'],
                        edit['version_id'],
                        edit['file_path'],
                        edit['sheet_name'],
                        edit['cell_address'],
                        json.dumps(edit['original_state']),
                        json.dumps(edit['cell_data']),
                        edit.get('intended_fill_color'),
                        now,
                        'pending'
                    ))
                logger.info(f"Batch created {len(edits)} pending edits")
                
                try:
                    # Execute batch insert
                    cursor.executemany('''
                        INSERT OR REPLACE INTO pending_edits 
                        (edit_id, version_id, file_path, sheet_name, cell_address,
                        original_state, cell_data, intended_fill_color, timestamp, status)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', batch_data)
                except sqlite3.Error as e:
                    logger.error(f"Execute batch insert failed with SQLITE error: {e}")
                    raise
                
                self.conn.commit()
                return [edit['edit_id'] for edit in edits]
                
        except (sqlite3.Error, json.JSONDecodeError) as e:
            self.conn.rollback()
            logger.error(f"Error batch creating pending edits: {e}")
            return []
    
    
    def close(self) -> None:
        """Close the database connection."""
        if hasattr(self, 'conn') and self.conn:
            try:
                self.conn.close()
                logger.info("Database connection closed")
            except Exception as e:
                logger.error(f"Error closing database connection: {e}")

    def __enter__(self):
        """Context manager entry."""
        return self
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def __del__(self):
        """Ensure connection is closed when object is destroyed."""
        try:
            self.close()
        except:
            pass