import sqlite3
import numpy as np
import json
import os
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import logging
logger = logging.getLogger(__name__)
from pathlib import Path

class EmbeddingStorage:
    """
    SQLite storage for Excel workbook embeddings and chunks.
    Modified to store both natural text and markdown formats.
    """
    
    def __init__(self, db_path: str = None, db_name: str = None):
        """Initialize the embedding storage
        
        Args:
            db_path: Path to the database directory
            db_name: Name of the database file
        """
        if db_path is None:
            base_dir = Path(__file__).parent.parent
            db_path = base_dir / "db"
            db_path.mkdir(exist_ok=True)  # Create directory if it doesn't exist
        if db_name is None:
            db_name = "excel_embeddings.db"

        self.db_path = os.path.join(db_path, db_name)
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)

        self.logger = logging.getLogger(__name__)
        
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        
        self.conn.execute("PRAGMA foreign_keys = ON")
        
        self._init_schema()

    def _init_schema(self):
        """Create database schema with dual format storage."""
        cursor = self.conn.cursor()
        
        # Workbooks table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS workbooks (
                workbook_id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT UNIQUE NOT NULL,
                file_name TEXT NOT NULL,
                file_hash TEXT,
                total_chunks INTEGER DEFAULT 0,
                embedding_dimension INTEGER,
                embedding_model TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                workbook_metadata TEXT
            )
        """)

        # Check if we need to drop and recreate the chunks table
        cursor.execute("PRAGMA table_info(chunks)")
        if cursor.fetchall():  # Table exists
            # Check if the unique constraint exists
            cursor.execute("""
                SELECT sql 
                FROM sqlite_master 
                WHERE type = 'table' 
                AND name = 'chunks'
            """)
            create_table_sql = cursor.fetchone()[0]
            
            # If the unique constraint exists in the table definition
            if 'UNIQUE(workbook_id, chunk_index)' in create_table_sql.upper():
                self.logger.info("Dropping and recreating chunks table to remove unique constraint")
                
                # Create a backup of the chunks table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS chunks_backup AS 
                    SELECT * FROM chunks
                """)
                
                # Drop the old table
                cursor.execute("DROP TABLE IF EXISTS chunks")
                
                # Create the new table without the unique constraint
                cursor.execute("""
                    CREATE TABLE chunks (
                        chunk_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        workbook_id INTEGER NOT NULL,
                        chunk_index INTEGER NOT NULL,
                        version_id INTEGER NOT NULL,                
                        chunk_text TEXT NOT NULL,
                        chunk_markdown TEXT NOT NULL,
                        embedding BLOB NOT NULL,
                        chunk_metadata TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (workbook_id) REFERENCES workbooks(workbook_id) ON DELETE CASCADE
                    )
                """)
                
                # Copy data back from backup
                cursor.execute("""
                    INSERT INTO chunks 
                    SELECT * FROM chunks_backup
                """)
                
                # Drop the backup
                cursor.execute("DROP TABLE chunks_backup")
        
        # Chunks table with both text formats
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chunks (
                chunk_id INTEGER PRIMARY KEY AUTOINCREMENT,
                workbook_id INTEGER NOT NULL,
                chunk_index INTEGER NOT NULL,
                version_id INTEGER NOT NULL,                
                chunk_text TEXT NOT NULL,         -- Natural language format
                chunk_markdown TEXT NOT NULL,     -- Markdown format
                embedding BLOB NOT NULL,
                chunk_metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (workbook_id) REFERENCES workbooks(workbook_id) ON DELETE CASCADE
            )
        """)

        # Add version_id column if it doesn't exist
        cursor.execute("PRAGMA table_info(chunks)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'version_id' not in columns:
            self.logger.info("Adding version_id column to chunks table")
            cursor.execute("ALTER TABLE chunks ADD COLUMN version_id INTEGER NOT NULL DEFAULT 1")


        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_workbook_id ON chunks(workbook_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_workbook_chunk ON chunks(workbook_id, chunk_index)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chunk_version ON chunks(workbook_id, version_id)")  # For version queries
        
        self.conn.commit()
        self.logger.info(f"Embeddings Database initialized at {self.db_path}")
    
    def add_workbook_embeddings(
        self,
        workbook_path: str,
        embeddings: np.ndarray,
        chunks: List[Dict[str, str]],
        embedding_model: str = "unknown",
        workbook_metadata: Optional[Dict] = None,
        create_new_version: bool = True,
        version_id: Optional[int] = None
    ) -> Tuple[int, int]:
        """
        Store embeddings and chunks for a workbook.
        Modified to store both text and markdown formats.
        
        Args:
            chunks: List of dictionaries with 'text', 'markdown', and 'metadata' keys
            version_id: Version ID for the workbook
            create_new_version: Whether to create a new version of the workbook
            workbook_metadata: Metadata for the workbook
            embedding_model: Embedding model used
            
        Returns:
            Tuple of (workbook_id, version_id)
        """
        cursor = self.conn.cursor()
        
        try:
            cursor.execute("BEGIN TRANSACTION")
            
            # Check if workbook exists
            cursor.execute("""
                SELECT workbook_id, COALESCE(MAX(version_id), 0) as latest_version 
                FROM workbooks 
                LEFT JOIN chunks USING(workbook_id) 
                WHERE file_path = ?
                GROUP BY workbook_id
            """, (workbook_path,))
            existing = cursor.fetchone()

            # Determine the new version ID
            if version_id is not None:
                new_version = version_id
            elif existing:
                new_version = existing['latest_version'] + 1 if create_new_version else existing['latest_version']
            else:
                new_version = 1

            # Insert or update workbook
            if not existing:
                self.logger.info(f"Inserting new workbook: {workbook_path} with version {new_version}")
                cursor.execute("""
                    INSERT INTO workbooks (
                        file_path, file_name, total_chunks, 
                        embedding_dimension, embedding_model, workbook_metadata
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    workbook_path,
                    os.path.basename(workbook_path),
                    len(chunks),
                    embeddings.shape[1],
                    embedding_model,
                    json.dumps(workbook_metadata) if workbook_metadata else None
                ))
                workbook_id = cursor.lastrowid
                self.logger.info(f"Inserted new workbook: {workbook_path} with version {new_version}")
            else:
                workbook_id = existing['workbook_id']
                if create_new_version:
                    self.logger.info(f"Versioning enabled. Updating existing workbook: {workbook_path} with version {new_version}")
                    cursor.execute("""
                        UPDATE workbooks 
                        SET total_chunks = ?, 
                            embedding_dimension = ?,
                            embedding_model = ?,
                            updated_at = CURRENT_TIMESTAMP,
                            workbook_metadata = ?
                        WHERE workbook_id = ?
                    """, (
                        len(chunks),
                        embeddings.shape[1],
                        embedding_model,
                        json.dumps(workbook_metadata) if workbook_metadata else None,
                        workbook_id
                    ))
                else:
                    # If not creating new version, delete existing chunks for this version
                    self.logger.info(f"Versioning disabled. Deleting existing chunks for workbook: {workbook_path} with version {new_version}")
                    cursor.execute("""
                        DELETE FROM chunks 
                        WHERE workbook_id = ? AND version_id = ?
                    """, (workbook_id, new_version))
            
            # Insert chunks with versioning
            chunk_data = []
            for i, (embedding, chunk) in enumerate(zip(embeddings, chunks)):
                embedding_bytes = embedding.astype(np.float32).tobytes()
                
                chunk_data.append((
                    workbook_id,
                    i,
                    new_version,  # Same version_id for all chunks in this batch
                    chunk['text'],
                    chunk['markdown'],
                    embedding_bytes,
                    json.dumps(chunk.get('metadata', {}))
                ))
            
            self.logger.info(f"Inserting {len(chunks)} chunks for workbook {workbook_path} (version {new_version})")
            cursor.executemany("""
                INSERT INTO chunks (
                    workbook_id, chunk_index, version_id, 
                    chunk_text, chunk_markdown, embedding, chunk_metadata
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, chunk_data)
            
            self.conn.commit()
            self.logger.info(f"Stored {len(chunks)} chunks for workbook {workbook_path} (version {new_version})")
            return workbook_id, new_version
            
        except Exception as e:
            self.conn.rollback()
            self.logger.error(f"Error storing embeddings: {str(e)}")
            raise

    def get_workbook_embeddings_by_version(
        self,
        workbook_path: str,
        version_id: int,
        return_format: str = 'both'
    ) -> Tuple[np.ndarray, List[Dict[str, any]]]:
        """Retrieve embeddings and chunks for a specific version of a workbook.
        
        Args:
            workbook_path: Path to the workbook file
            version_id: Version ID to retrieve
            return_format: Which text format to return ('text', 'markdown', or 'both')
            
        Returns:
            Tuple of (embeddings, chunks)
        """
        cursor = self.conn.cursor()
        
        # Get workbook_id
        cursor.execute("SELECT workbook_id FROM workbooks WHERE file_path = ?", (workbook_path,))
        workbook = cursor.fetchone()
        if not workbook:
            logger.error(f"Workbook not found: {workbook_path}")
            return None, None
        
        workbook_id = workbook['workbook_id']
        
        # Get chunks for this version
        cursor.execute("""
            SELECT 
                chunk_id, chunk_index, 
                chunk_text, chunk_markdown, 
                embedding, chunk_metadata
            FROM chunks
            WHERE workbook_id = ? AND version_id = ?
            ORDER BY chunk_index
        """, (workbook_id, version_id))
        
        chunks = []
        embeddings = []
        
        for row in cursor:
            # Convert blob back to numpy array
            embedding = np.frombuffer(row['embedding'], dtype=np.float32)
            embeddings.append(embedding)
            
            chunk_data = {
                'chunk_id': row['chunk_id'],
                'chunk_index': row['chunk_index'],
                'metadata': json.loads(row['chunk_metadata']) if row['chunk_metadata'] else {}
            }
            
            if return_format in ['text', 'both']:
                chunk_data['text'] = row['chunk_text']
            if return_format in ['markdown', 'both']:
                chunk_data['markdown'] = row['chunk_markdown']
                
            chunks.append(chunk_data)
        
        if not chunks:
            logger.error(f"No chunks found for workbook {workbook_path} (version {version_id})")
            return np.array([]), []
        
        logger.info(f"Retrieved {len(chunks)} chunks for workbook {workbook_path} (version {version_id})")
        return np.vstack(embeddings), chunks

    def get_latest_workbook_embeddings(
        self,
        workbook_path: str,
        return_format: str = 'both'
    ) -> Tuple[np.ndarray, List[Dict[str, any]]]:
        """Retrieve embeddings and chunks for the latest version of a workbook.
        
        Args:
            workbook_path: Path to the workbook file
            return_format: Which text format to return ('text', 'markdown', or 'both')
            
        Returns:
            Tuple of (embeddings, chunks)
        """
        cursor = self.conn.cursor()
        
        # Get workbook_id and latest version
        cursor.execute("""
            SELECT w.workbook_id, MAX(c.version_id) as latest_version
            FROM workbooks w
            LEFT JOIN chunks c ON w.workbook_id = c.workbook_id
            WHERE w.file_path = ?
            GROUP BY w.workbook_id
        """, (workbook_path,))
        
        result = cursor.fetchone()
        if not result or result['latest_version'] is None:
            logger.error(f"No versions found for workbook: {workbook_path}")
            return np.array([]), []
        
        workbook_id = result['workbook_id']
        latest_version = result['latest_version']
        
        # Get chunks for the latest version
        cursor.execute("""
            SELECT 
                chunk_id, chunk_index, 
                chunk_text, chunk_markdown, 
                embedding, chunk_metadata
            FROM chunks
            WHERE workbook_id = ? AND version_id = ?
            ORDER BY chunk_index
        """, (workbook_id, latest_version))
        
        chunks = []
        embeddings = []
        
        for row in cursor:
            # Convert blob back to numpy array
            embedding = np.frombuffer(row['embedding'], dtype=np.float32)
            embeddings.append(embedding)
            
            chunk_data = {
                'chunk_id': row['chunk_id'],
                'chunk_index': row['chunk_index'],
                'version_id': latest_version,
                'metadata': json.loads(row['chunk_metadata']) if row['chunk_metadata'] else {}
            }
            
            if return_format in ['text', 'both']:
                chunk_data['text'] = row['chunk_text']
            if return_format in ['markdown', 'both']:
                chunk_data['markdown'] = row['chunk_markdown']
                
            chunks.append(chunk_data)
        
        if not chunks:
            logger.error(f"No chunks found for workbook {workbook_path} (latest version {latest_version})")
            return np.array([]), []
        
        logger.info(f"Retrieved {len(chunks)} chunks for workbook {workbook_path} (latest version {latest_version})")
        return np.vstack(embeddings), chunks


    def list_workbook_versions(self, workbook_path: str) -> List[Dict[str, any]]:
        """List all versions of a workbook.
        
        Args:
            workbook_path: Path to the workbook file
            
        Returns:
            List of version information dictionaries
        """
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT 
                v.version_id,
                v.chunk_count,
                v.created_at,
                w.embedding_model,
                w.embedding_dimension
            FROM (
                SELECT 
                    version_id,
                    COUNT(*) as chunk_count,
                    MIN(created_at) as created_at
                FROM chunks
                WHERE workbook_id = (SELECT workbook_id FROM workbooks WHERE file_path = ?)
                GROUP BY version_id
            ) v
            CROSS JOIN workbooks w
            WHERE w.file_path = ?
            ORDER BY v.version_id DESC
        """, (workbook_path, workbook_path))
        
        return [dict(row) for row in cursor]
    
    def get_chunks_by_ids(self, chunk_ids: List[int], return_format: str = 'both') -> List[Dict[str, any]]:
        """
        Retrieve specific chunks by their IDs.
        Modified to return both text formats.
        """
        if not chunk_ids:
            return []
        
        cursor = self.conn.cursor()
        
        placeholders = ','.join(['?' for _ in chunk_ids])
        
        cursor.execute(f"""
            SELECT 
                c.chunk_id,
                c.chunk_index,
                c.chunk_text,
                c.chunk_markdown,
                c.chunk_metadata,
                w.file_path,
                w.file_name,
                w.embedding_model
            FROM chunks c
            JOIN workbooks w ON c.workbook_id = w.workbook_id
            WHERE c.chunk_id IN ({placeholders})
        """, chunk_ids)
        
        chunks = []
        for row in cursor:
            chunk_dict = {
                'chunk_id': row['chunk_id'],
                'chunk_index': row['chunk_index'],
                'metadata': json.loads(row['chunk_metadata']),
                'workbook_path': row['file_path'],
                'workbook_name': row['file_name'],
                'embedding_model': row['embedding_model']
            }
            
            if return_format == 'text':
                chunk_dict['text'] = row['chunk_text']
            elif return_format == 'markdown':
                chunk_dict['markdown'] = row['chunk_markdown']
            else:  # 'both'
                chunk_dict['text'] = row['chunk_text']
                chunk_dict['markdown'] = row['chunk_markdown']
            
            chunks.append(chunk_dict)
        
        return chunks
    
    def get_all_embeddings_for_faiss(self) -> Tuple[np.ndarray, List[int]]:
        """Get all embeddings in the database formatted for FAISS indexing."""
        cursor = self.conn.cursor()
        
        # Get the latest version for each workbook and join with chunks
        cursor.execute("""
            WITH latest_versions AS (
                SELECT 
                    workbook_id,
                    MAX(version_id) as latest_version
                FROM chunks
                GROUP BY workbook_id
            )
            SELECT 
                c.chunk_id, 
                c.embedding
            FROM chunks c
            INNER JOIN latest_versions lv 
                ON c.workbook_id = lv.workbook_id 
                AND c.version_id = lv.latest_version
            ORDER BY c.chunk_id
        """)
            
        embeddings = []
        chunk_ids = []
        
        for row in cursor:
            embedding = np.frombuffer(row['embedding'], dtype=np.float32)
            embeddings.append(embedding)
            chunk_ids.append(row['chunk_id'])
        
        if embeddings:
            return np.vstack(embeddings), chunk_ids
        else:
            return np.array([]), []
    
    def list_workbooks(self) -> List[Dict[str, any]]:
        """List all workbooks in the database."""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT 
                workbook_id,
                file_path,
                file_name,
                total_chunks,
                embedding_dimension,
                embedding_model,
                created_at,
                updated_at
            FROM workbooks
            ORDER BY updated_at DESC
        """)
        
        workbooks = []
        for row in cursor:
            workbooks.append({
                'workbook_id': row['workbook_id'],
                'file_path': row['file_path'],
                'file_name': row['file_name'],
                'total_chunks': row['total_chunks'],
                'embedding_dimension': row['embedding_dimension'],
                'embedding_model': row['embedding_model'],
                'created_at': row['created_at'],
                'updated_at': row['updated_at']
            })
        
        return workbooks
    
    def delete_workbook(self, workbook_path: str):
        """Delete a workbook and all its chunks."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM workbooks WHERE file_path = ?", (workbook_path,))
        self.conn.commit()
        self.logger.info(f"Deleted workbook: {workbook_path}")
    
    def close(self):
        """Close database connection."""
        self.conn.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()