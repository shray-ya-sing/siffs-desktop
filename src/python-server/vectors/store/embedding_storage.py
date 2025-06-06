import sqlite3
import numpy as np
import json
import os
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import logging

class EmbeddingStorage:
    """
    SQLite storage for Excel workbook embeddings and chunks.
    Modified to store both natural text and markdown formats.
    """
    
    def __init__(self, db_path: str = "./excel_embeddings.db"):
        """Initialize the embedding storage."""
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
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
        
        # Chunks table with both text formats
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chunks (
                chunk_id INTEGER PRIMARY KEY AUTOINCREMENT,
                workbook_id INTEGER NOT NULL,
                chunk_index INTEGER NOT NULL,
                chunk_text TEXT NOT NULL,         -- Natural language format
                chunk_markdown TEXT NOT NULL,     -- Markdown format
                embedding BLOB NOT NULL,
                chunk_metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (workbook_id) REFERENCES workbooks(workbook_id) ON DELETE CASCADE,
                UNIQUE(workbook_id, chunk_index)
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_workbook_id ON chunks(workbook_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_workbook_chunk ON chunks(workbook_id, chunk_index)")
        
        self.conn.commit()
        self.logger.info(f"Database initialized at {self.db_path}")
    
    def add_workbook_embeddings(
        self,
        workbook_path: str,
        embeddings: np.ndarray,
        chunks: List[Dict[str, str]],
        embedding_model: str = "unknown",
        workbook_metadata: Optional[Dict] = None,
        replace_existing: bool = True
    ) -> int:
        """
        Store embeddings and chunks for a workbook.
        Modified to store both text and markdown formats.
        
        Args:
            chunks: List of dictionaries with 'text', 'markdown', and 'metadata' keys
        """
        cursor = self.conn.cursor()
        
        try:
            cursor.execute("BEGIN TRANSACTION")
            
            # Check if workbook exists
            cursor.execute("SELECT workbook_id FROM workbooks WHERE file_path = ?", (workbook_path,))
            existing = cursor.fetchone()
            
            if existing and replace_existing:
                workbook_id = existing['workbook_id']
                cursor.execute("DELETE FROM chunks WHERE workbook_id = ?", (workbook_id,))
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
            elif existing and not replace_existing:
                self.logger.warning(f"Workbook {workbook_path} already exists. Set replace_existing=True to overwrite.")
                return existing['workbook_id']
            else:
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
            
            # Insert chunks with both formats
            chunk_data = []
            for i, (embedding, chunk) in enumerate(zip(embeddings, chunks)):
                embedding_bytes = embedding.astype(np.float32).tobytes()
                
                chunk_data.append((
                    workbook_id,
                    i,
                    chunk['text'],      # Natural language text
                    chunk['markdown'],  # Markdown format
                    embedding_bytes,
                    json.dumps(chunk.get('metadata', {}))
                ))
            
            cursor.executemany("""
                INSERT INTO chunks (workbook_id, chunk_index, chunk_text, chunk_markdown, embedding, chunk_metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            """, chunk_data)
            
            self.conn.commit()
            
            self.logger.info(f"Stored {len(chunks)} chunks for workbook: {os.path.basename(workbook_path)}")
            return workbook_id
            
        except Exception as e:
            self.conn.rollback()
            self.logger.error(f"Error storing embeddings: {str(e)}")
            raise
    
    def get_workbook_embeddings(
        self, 
        workbook_path: str,
        return_format: str = 'both'  # 'text', 'markdown', or 'both'
    ) -> Tuple[np.ndarray, List[Dict[str, any]], Dict[str, any]]:
        """
        Retrieve all embeddings and chunks for a workbook.
        
        Args:
            workbook_path: Path to the Excel file
            return_format: Which text format to return
        """
        cursor = self.conn.cursor()
        
        cursor.execute("SELECT * FROM workbooks WHERE file_path = ?", (workbook_path,))
        workbook_info = cursor.fetchone()
        if not workbook_info:
            raise ValueError(f"Workbook not found: {workbook_path}")
        
        cursor.execute("""
            SELECT chunk_index, chunk_text, chunk_markdown, embedding, chunk_metadata
            FROM chunks
            WHERE workbook_id = ?
            ORDER BY chunk_index
        """, (workbook_info['workbook_id'],))
        
        embeddings = []
        chunks = []
        
        for row in cursor:
            embedding = np.frombuffer(row['embedding'], dtype=np.float32)
            embeddings.append(embedding)
            
            chunk_dict = {
                'chunk_index': row['chunk_index'],
                'metadata': json.loads(row['chunk_metadata'])
            }
            
            if return_format == 'text':
                chunk_dict['text'] = row['chunk_text']
            elif return_format == 'markdown':
                chunk_dict['markdown'] = row['chunk_markdown']
            else:  # 'both'
                chunk_dict['text'] = row['chunk_text']
                chunk_dict['markdown'] = row['chunk_markdown']
            
            chunks.append(chunk_dict)
        
        workbook_dict = {
            'workbook_id': workbook_info['workbook_id'],
            'file_path': workbook_info['file_path'],
            'file_name': workbook_info['file_name'],
            'total_chunks': workbook_info['total_chunks'],
            'embedding_dimension': workbook_info['embedding_dimension'],
            'embedding_model': workbook_info['embedding_model'],
            'created_at': workbook_info['created_at'],
            'updated_at': workbook_info['updated_at'],
            'metadata': json.loads(workbook_info['workbook_metadata']) if workbook_info['workbook_metadata'] else None
        }
        
        if embeddings:
            embeddings_array = np.vstack(embeddings)
            return embeddings_array, chunks, workbook_dict
        else:
            return np.array([]), [], workbook_dict
    
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
        
        cursor.execute("""
            SELECT chunk_id, embedding
            FROM chunks
            ORDER BY chunk_id
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