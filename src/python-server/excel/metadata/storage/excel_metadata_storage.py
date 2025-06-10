from pathlib import Path
import os
import sqlite3
import json
from typing import Optional, List, Dict, Set
import atexit
import threading
import hashlib
from datetime import datetime
import re

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
                    required_tables = {'workbooks', 'file_versions', 'chunks', 'cells'}
                    cursor.execute("""
                        SELECT name FROM sqlite_master 
                        WHERE type='table' AND name IN (?, ?, ?, ?)
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
                
                -- Create indexes
                CREATE INDEX idx_chunks_version_id ON chunks(version_id);
                CREATE INDEX idx_cells_version_sheet ON cells(version_id, sheet_name);
                CREATE INDEX idx_file_versions_workbook ON file_versions(workbook_id);
                
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

    def close(self):
        """Close the database connection."""
        if hasattr(self, 'conn'):
            try:
                with self._lock:
                    if self.conn:
                        self.conn.close()
                        self.conn = None
            except Exception as e:
                print(f"Error closing database connection: {e}")

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