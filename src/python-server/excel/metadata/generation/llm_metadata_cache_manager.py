# Add these imports at the top of the file
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional, Union, AsyncGenerator, List
import hashlib
import json
import time
from collections import OrderedDict
import logging
from pathlib import Path
import os

@dataclass
class CacheEntry:
    """Represents a single cache entry with metadata."""
    metadata: str
    timestamp: float
    usage_count: int = 0

class LLMMetadataCacheManager:
    """
    Manages caching for LLM metadata generation with TTL and LRU eviction.
    
    Attributes:
        max_size: Maximum number of cache entries to store
        ttl_seconds: Time-to-live for cache entries in seconds
    """
    
    def __init__(self, 
        max_size: int = 1000, 
        ttl_seconds: int = 3600,
        auto_save: bool = True,
        save_interval: int = 60
    ):
        """
        Initialize the cache manager.
        
        Args:
            max_size: Maximum number of cache entries
            ttl_seconds: Time-to-live for cache entries in seconds
            auto_save: Whether to automatically save the cache to disk
            save_interval: Interval in seconds between automatic saves
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._hits = 0
        self._misses = 0
        self._logger = logging.getLogger('LLMMetadataCache')
        self.cache_dir = Path(__file__).parent.parent / "_cache"
        os.makedirs(self.cache_dir, exist_ok=True)
        self.auto_save = auto_save
        self.save_interval = save_interval
        self._last_save_time = 0
        self._modified = False

    def _get_cache_filepath(self) -> Path:
        """Get the default cache file path."""
        return self.cache_dir / "llm_metadata_cache.json"
    
    def _should_save(self) -> bool:
        """Check if we should save the cache based on time and modifications."""
        if not self.auto_save or not self._modified:
            return False
        return (time.time() - self._last_save_time) >= self.save_interval

    def _auto_save(self) -> None:
        """Save the cache if auto-save is enabled and needed."""
        if self._should_save():
            self.save_to_file(self._get_cache_filepath())
            self._modified = False
            self._last_save_time = time.time()

    def mark_modified(self) -> None:
        """Mark the cache as modified to trigger auto-save."""
        self._modified = True
        self._auto_save()  # Try to save immediately
        
    def _generate_key(self, *args, **kwargs) -> str:
        """
        Generate a unique cache key from the provided arguments.
        
        Args:
            *args: Positional arguments to include in the key
            **kwargs: Keyword arguments to include in the key
            
        Returns:
            SHA-256 hash of the serialized arguments
        """
        key_data = {
            'args': args,
            'kwargs': {k: v for k, v in sorted(kwargs.items()) if k != 'use_cache'}
        }
        serialized = json.dumps(key_data, sort_keys=True).encode()
        return hashlib.sha256(serialized).hexdigest()

    def _is_expired(self, entry: CacheEntry) -> bool:
        """Check if a cache entry has expired."""
        return (time.time() - entry.timestamp) > self.ttl_seconds

    def _cleanup(self) -> None:
        """Remove expired entries and enforce max size."""
        now = time.time()
        
        # Remove expired entries
        expired_keys = [
            key for key, entry in self._cache.items()
            if (now - entry.timestamp) > self.ttl_seconds
        ]
        for key in expired_keys:
            del self._cache[key]
            self._logger.debug(f"Expired cache entry removed: {key[:8]}...")
        
        # Enforce max size by removing oldest entries
        while len(self._cache) > self.max_size:
            self._cache.popitem(last=False)

    def get(self, key: str) -> Optional[str]:
        """
        Retrieve a value from the cache.
        
        Args:
            key: Cache key to look up
            
        Returns:
            Cached value if found and not expired, None otherwise
        """
        entry = self._cache.get(key)
        
        if entry is None:
            self._misses += 1
            return None
            
        if self._is_expired(entry):
            del self._cache[key]
            self._misses += 1
            return None
            
        # Update usage stats and move to end (most recently used)
        entry.usage_count += 1
        entry.timestamp = time.time()
        self._cache.move_to_end(key)
        self._hits += 1
        
        return entry.metadata

    def set(self, key: str, value: str) -> None:
        """
        Store a value in the cache.
        
        Args:
            key: Cache key
            value: Value to cache
        """
        self._cleanup()  # Clean up before adding new entry
        
        self._cache[key] = CacheEntry(
            metadata=value,
            timestamp=time.time()
        )
        # Move to end to maintain LRU order
        self._cache.move_to_end(key)
        self.mark_modified()

    def clear(self, older_than: Optional[float] = None) -> int:
        """
        Clear cache entries.
        
        Args:
            older_than: If provided, only clear entries older than this timestamp.
                       If None, clear all entries.
                       
        Returns:
            Number of entries removed
        """
        if older_than is None:
            count = len(self._cache)
            self._cache.clear()
            return count
            
        before = len(self._cache)
        self._cache = OrderedDict(
            (k, v) for k, v in self._cache.items()
            if v.timestamp >= older_than
        )
        return before - len(self._cache)

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        now = time.time()
        return {
            "total_entries": len(self._cache),
            "hits": self._hits,
            "misses": self._misses,
            "hit_ratio": self._hits / (self._hits + self._misses) if (self._hits + self._misses) > 0 else 0,
            "oldest_entry": min((e.timestamp for e in self._cache.values()), default=0),
            "newest_entry": max((e.timestamp for e in self._cache.values()), default=0),
            "expired_entries": sum(1 for e in self._cache.values() 
                                 if (now - e.timestamp) > self.ttl_seconds)
        }

    def save_to_file(self, filepath: Optional[str] = None) -> bool:
        """
        Save cache to a file.
        
        Args:
            filepath: Path to save the cache to
            
        Returns:
            True if save was successful, False otherwise
        """
        
        if filepath is None:
            filepath = self._get_cache_filepath()
        
        try:
            with open(filepath, 'w') as f:
                json.dump({
                    "entries": {
                        k: asdict(v) for k, v in self._cache.items()
                    },
                    "config": {
                        "max_size": self.max_size,
                        "ttl_seconds": self.ttl_seconds,
                        "hits": self._hits,
                        "misses": self._misses
                    }
                }, f)
            self._modified = False
            self._last_save_time = time.time()
            self._logger.info(f"Cache saved to {filepath}")
            return True
        except Exception as e:
            self._logger.error(f"Failed to save cache: {e}")
            return False

    def close(self) -> None:
        """Close the cache and perform final save if needed."""
        if self.auto_save and self._modified:
            self.save_to_file(self._get_cache_filepath())
            self._logger.info("Cache saved on close")

    # Add context manager support
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    @classmethod
    def load_from_file(cls, filepath: Optional[str] = None) -> 'LLMMetadataCacheManager':
        """
        Load cache from a file.
        
        Args:
            filepath: Path to load the cache from
            
        Returns:
            New LLMMetadataCacheManager instance with loaded cache
        """
        instance = cls()
        try:
            if filepath is None:
                filepath = instance._get_cache_filepath()
            
            if os.path.exists(filepath):
                with open(filepath, 'r') as f:
                    data = json.load(f)
            
                config = data.get("config", {})
                instance = cls(
                    max_size=config.get("max_size", 1000),
                    ttl_seconds=config.get("ttl_seconds", 3600)
                )
                
                instance._cache = OrderedDict(
                    (k, CacheEntry(**v)) 
                    for k, v in data.get("entries", {}).items()
                )
                instance._hits = config.get("hits", 0)
                instance._misses = config.get("misses", 0)
            
            return instance
        except Exception as e:
            logger = logging.getLogger('LLMMetadataCache')
            logger.error(f"Failed to load cache: {e}")
            # Return empty cache if loading fails
            return instance