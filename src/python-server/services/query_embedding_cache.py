# Siffs - Fast File Search Desktop Application
# Copyright (C) 2025  Siffs
# 
# Contact: github.suggest277@passinbox.com
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import os
import json
import hashlib
import logging
import time
from typing import List, Optional, Dict, Any
from pathlib import Path
from threading import Lock
import pickle

logger = logging.getLogger(__name__)

class QueryEmbeddingCache:
    """
    High-performance query embedding cache with memory and disk persistence
    
    Features:
    - In-memory cache for ultra-fast access
    - Disk persistence across app restarts
    - LRU (Least Recently Used) eviction policy
    - Configurable cache size limits
    - Thread-safe operations
    - Query normalization for better cache hits
    """
    
    def __init__(self, 
                 cache_dir: str = None,
                 max_memory_entries: int = 1000,
                 max_disk_entries: int = 5000,
                 max_disk_size_mb: int = 100):
        """
        Initialize the query embedding cache
        
        Args:
            cache_dir: Directory to store persistent cache (if None, uses default app data)
            max_memory_entries: Maximum entries to keep in memory
            max_disk_entries: Maximum entries to keep on disk
            max_disk_size_mb: Maximum disk cache size in MB
        """
        # Set up cache directory
        if cache_dir is None:
            # Use platform-appropriate app data directory
            if os.name == 'nt':  # Windows
                app_data = os.getenv('LOCALAPPDATA', os.path.expanduser('~\\AppData\\Local'))
                cache_dir = os.path.join(app_data, 'SIFFS', 'query_cache')
            else:  # Mac/Linux
                app_data = os.path.expanduser('~/.local/share')
                cache_dir = os.path.join(app_data, 'SIFFS', 'query_cache')
        
        # Create directory if it doesn't exist
        os.makedirs(cache_dir, exist_ok=True)
        
        self.cache_dir = cache_dir
        self.max_memory_entries = max_memory_entries
        self.max_disk_entries = max_disk_entries
        self.max_disk_size_mb = max_disk_size_mb
        
        # In-memory cache: {query_hash: (embedding, timestamp, access_count)}
        self._memory_cache: Dict[str, tuple] = {}
        
        # Disk cache metadata: {query_hash: (file_path, timestamp, access_count, file_size)}
        self._disk_index: Dict[str, tuple] = {}
        
        # Thread safety
        self._lock = Lock()
        
        # Cache statistics
        self.stats = {
            'memory_hits': 0,
            'disk_hits': 0,
            'misses': 0,
            'total_queries': 0,
            'cache_saves': 0
        }
        
        # Initialize cache
        self._load_disk_index()
        logger.info(f"✅ Query embedding cache initialized")
        logger.info(f"   Cache directory: {cache_dir}")
        logger.info(f"   Memory limit: {max_memory_entries} entries")
        logger.info(f"   Disk limit: {max_disk_entries} entries, {max_disk_size_mb}MB")
        logger.info(f"   Loaded {len(self._disk_index)} cached queries from disk")
    
    def _normalize_query(self, query: str) -> str:
        """Normalize query text for consistent caching"""
        # Convert to lowercase, strip whitespace, normalize multiple spaces
        normalized = ' '.join(query.lower().strip().split())
        return normalized
    
    def _get_query_hash(self, query: str) -> str:
        """Generate a unique hash for the query"""
        normalized_query = self._normalize_query(query)
        return hashlib.sha256(normalized_query.encode('utf-8')).hexdigest()
    
    def _load_disk_index(self):
        """Load disk cache index from metadata file"""
        try:
            index_file = os.path.join(self.cache_dir, 'cache_index.json')
            if os.path.exists(index_file):
                with open(index_file, 'r', encoding='utf-8') as f:
                    self._disk_index = json.load(f)
                
                # Clean up invalid entries (files that no longer exist)
                valid_entries = {}
                for query_hash, (file_path, timestamp, access_count, file_size) in self._disk_index.items():
                    full_path = os.path.join(self.cache_dir, file_path)
                    if os.path.exists(full_path):
                        valid_entries[query_hash] = (file_path, timestamp, access_count, file_size)
                    else:
                        logger.debug(f"Removing stale cache entry: {file_path}")
                
                self._disk_index = valid_entries
                logger.info(f"📂 Loaded {len(self._disk_index)} valid cache entries from disk")
            else:
                logger.info("📂 No existing disk cache found, starting fresh")
                
        except Exception as e:
            logger.warning(f"⚠️ Failed to load disk cache index: {e}")
            self._disk_index = {}
    
    def _save_disk_index(self):
        """Save disk cache index to metadata file"""
        try:
            index_file = os.path.join(self.cache_dir, 'cache_index.json')
            with open(index_file, 'w', encoding='utf-8') as f:
                json.dump(self._disk_index, f, indent=2)
            logger.debug("💾 Saved disk cache index")
        except Exception as e:
            logger.error(f"❌ Failed to save disk cache index: {e}")
    
    def _evict_memory_cache(self):
        """Evict least recently used entries from memory cache"""
        if len(self._memory_cache) <= self.max_memory_entries:
            return
        
        # Sort by last access time (timestamp) and remove oldest entries
        sorted_entries = sorted(
            self._memory_cache.items(),
            key=lambda x: x[1][1]  # Sort by timestamp
        )
        
        # Remove oldest entries
        entries_to_remove = len(self._memory_cache) - self.max_memory_entries
        for i in range(entries_to_remove):
            query_hash = sorted_entries[i][0]
            del self._memory_cache[query_hash]
            logger.debug(f"🗑️ Evicted memory cache entry: {query_hash[:8]}...")
        
        logger.info(f"🧹 Memory cache eviction: removed {entries_to_remove} entries")
    
    def _evict_disk_cache(self):
        """Evict least recently used entries from disk cache"""
        if len(self._disk_index) <= self.max_disk_entries:
            return
        
        # Sort by last access time and remove oldest entries
        sorted_entries = sorted(
            self._disk_index.items(),
            key=lambda x: x[1][1]  # Sort by timestamp
        )
        
        # Remove oldest entries
        entries_to_remove = len(self._disk_index) - self.max_disk_entries
        for i in range(entries_to_remove):
            query_hash, (file_path, _, _, _) = sorted_entries[i]
            
            # Delete the actual file
            full_path = os.path.join(self.cache_dir, file_path)
            try:
                if os.path.exists(full_path):
                    os.remove(full_path)
                del self._disk_index[query_hash]
                logger.debug(f"🗑️ Evicted disk cache entry: {query_hash[:8]}...")
            except Exception as e:
                logger.warning(f"⚠️ Failed to remove cache file {file_path}: {e}")
        
        logger.info(f"🧹 Disk cache eviction: removed {entries_to_remove} entries")
        self._save_disk_index()
    
    def get_embedding(self, query: str) -> Optional[List[float]]:
        """
        Get cached embedding for a query
        
        Args:
            query: Search query text
            
        Returns:
            Cached embedding if found, None otherwise
        """
        with self._lock:
            self.stats['total_queries'] += 1
            query_hash = self._get_query_hash(query)
            current_time = time.time()
            
            # Check memory cache first
            if query_hash in self._memory_cache:
                embedding, _, access_count = self._memory_cache[query_hash]
                # Update access info
                self._memory_cache[query_hash] = (embedding, current_time, access_count + 1)
                self.stats['memory_hits'] += 1
                logger.debug(f"🚀 Memory cache HIT for query: '{query[:50]}...'")
                return embedding
            
            # Check disk cache
            if query_hash in self._disk_index:
                file_path, _, access_count, _ = self._disk_index[query_hash]
                full_path = os.path.join(self.cache_dir, file_path)
                
                try:
                    # Load embedding from disk
                    with open(full_path, 'rb') as f:
                        embedding = pickle.load(f)
                    
                    # Update access info
                    file_size = os.path.getsize(full_path)
                    self._disk_index[query_hash] = (file_path, current_time, access_count + 1, file_size)
                    
                    # Add to memory cache for faster future access
                    self._memory_cache[query_hash] = (embedding, current_time, access_count + 1)
                    self._evict_memory_cache()
                    
                    self.stats['disk_hits'] += 1
                    logger.debug(f"💾 Disk cache HIT for query: '{query[:50]}...', loaded to memory")
                    return embedding
                    
                except Exception as e:
                    logger.warning(f"⚠️ Failed to load embedding from disk cache: {e}")
                    # Remove invalid entry
                    del self._disk_index[query_hash]
                    self._save_disk_index()
            
            # Cache miss
            self.stats['misses'] += 1
            logger.debug(f"❌ Cache MISS for query: '{query[:50]}...'")
            return None
    
    def cache_embedding(self, query: str, embedding: List[float]):
        """
        Cache an embedding for a query
        
        Args:
            query: Search query text
            embedding: Query embedding vector
        """
        with self._lock:
            query_hash = self._get_query_hash(query)
            current_time = time.time()
            
            # Add to memory cache
            self._memory_cache[query_hash] = (embedding, current_time, 1)
            self._evict_memory_cache()
            
            # Save to disk cache
            try:
                file_name = f"query_{query_hash}.pkl"
                file_path = os.path.join(self.cache_dir, file_name)
                
                with open(file_path, 'wb') as f:
                    pickle.dump(embedding, f, protocol=pickle.HIGHEST_PROTOCOL)
                
                file_size = os.path.getsize(file_path)
                self._disk_index[query_hash] = (file_name, current_time, 1, file_size)
                
                # Check if we need to evict disk cache
                self._evict_disk_cache()
                self._save_disk_index()
                
                self.stats['cache_saves'] += 1
                logger.debug(f"💾 Cached embedding for query: '{query[:50]}...' (size: {file_size} bytes)")
                
            except Exception as e:
                logger.error(f"❌ Failed to cache embedding to disk: {e}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics"""
        with self._lock:
            total_requests = self.stats['total_queries']
            hit_rate = 0.0
            if total_requests > 0:
                total_hits = self.stats['memory_hits'] + self.stats['disk_hits']
                hit_rate = (total_hits / total_requests) * 100
            
            # Calculate disk usage
            disk_size_bytes = sum(file_size for _, _, _, file_size in self._disk_index.values())
            disk_size_mb = disk_size_bytes / (1024 * 1024)
            
            return {
                'memory_entries': len(self._memory_cache),
                'disk_entries': len(self._disk_index),
                'disk_size_mb': round(disk_size_mb, 2),
                'hit_rate_percent': round(hit_rate, 1),
                'memory_hits': self.stats['memory_hits'],
                'disk_hits': self.stats['disk_hits'],
                'misses': self.stats['misses'],
                'total_queries': self.stats['total_queries'],
                'cache_saves': self.stats['cache_saves']
            }
    
    def clear_cache(self):
        """Clear all cached embeddings"""
        with self._lock:
            # Clear memory cache
            self._memory_cache.clear()
            
            # Clear disk cache
            try:
                for _, (file_path, _, _, _) in self._disk_index.items():
                    full_path = os.path.join(self.cache_dir, file_path)
                    if os.path.exists(full_path):
                        os.remove(full_path)
                
                self._disk_index.clear()
                self._save_disk_index()
                
                logger.info("🧹 Cleared all cached embeddings")
                
            except Exception as e:
                logger.error(f"❌ Error clearing disk cache: {e}")
    
    def cleanup(self):
        """Cleanup cache resources"""
        with self._lock:
            self._save_disk_index()
            logger.info("🔧 Query embedding cache cleanup completed")


# Global cache instance
_query_cache = None

def get_query_embedding_cache() -> QueryEmbeddingCache:
    """Get or create global query embedding cache"""
    global _query_cache
    if _query_cache is None:
        _query_cache = QueryEmbeddingCache()
    return _query_cache
