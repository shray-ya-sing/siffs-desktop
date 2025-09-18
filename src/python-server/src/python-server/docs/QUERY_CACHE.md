# Query Embedding Cache

The SIFFS backend includes a high-performance query embedding cache that automatically accelerates repeated searches by caching query embeddings from VoyageAI.

## Overview

When users search for slides, the system needs to convert their text queries into embeddings using VoyageAI's API. This cache eliminates redundant API calls by storing and reusing embeddings for identical or similar queries.

## Key Features

### 🚀 **Performance Boost**
- **~10x faster** for repeated queries (cache hits vs API calls)  
- Automatic transparent caching - no code changes needed
- Significantly reduces API latency for common queries

### 💾 **Two-Tier Storage**
- **Memory Cache**: Ultra-fast access to recently used queries
- **Disk Cache**: Persistent storage that survives app restarts
- Intelligent promotion from disk to memory for better performance

### 🧠 **Smart Query Normalization** 
- Automatically normalizes queries for better cache hit rates:
  - `"Machine Learning"` → `"machine learning"`
  - `"  AI   trends  "` → `"ai trends"`  
  - Case-insensitive matching
  - Whitespace normalization

### 📊 **LRU Eviction Policy**
- Automatically removes least recently used entries when limits are reached
- Configurable memory and disk size limits
- Graceful degradation under memory pressure

### 🔒 **Thread Safety**
- Safe for concurrent access from multiple search requests
- Uses proper locking mechanisms

## Architecture

```
[User Search Query] 
       ↓
[Query Normalization] 
       ↓
[Check Memory Cache] ──── Cache Hit ────→ [Return Embedding]
       ↓ Cache Miss
[Check Disk Cache] ───── Cache Hit ────→ [Load to Memory] → [Return Embedding]  
       ↓ Cache Miss
[VoyageAI API Call] 
       ↓
[Cache Result] → [Return Embedding]
```

## Configuration

The cache is automatically initialized with sensible defaults:

```python
QueryEmbeddingCache(
    max_memory_entries=1000,    # Keep 1000 embeddings in memory
    max_disk_entries=5000,      # Keep 5000 embeddings on disk  
    max_disk_size_mb=100        # Limit disk cache to 100MB
)
```

### Cache Location

**Windows**: `%LOCALAPPDATA%\SIFFS\query_cache\`  
**macOS/Linux**: `~/.local/share/SIFFS/query_cache/`

## Implementation Details

### Files Structure
```
query_cache/
├── cache_index.json          # Metadata index
├── query_<hash1>.pkl         # Embedding files
├── query_<hash2>.pkl
└── ...
```

### Query Hashing
- Uses SHA-256 hashing of normalized queries
- Ensures consistent cache keys across sessions
- Handles Unicode text properly

### Embedding Storage
- Uses Python's `pickle` with highest protocol for efficiency
- Each embedding file contains a 1536-dimensional float vector (VoyageAI format)
- Typical file size: ~14KB per embedding

## Performance Metrics

From testing with realistic queries:

| Metric | Value |
|--------|-------|
| Cache Hit Speedup | ~10x faster |
| Memory Access Time | < 1ms |
| Disk Access Time | < 25ms |
| VoyageAI API Time | 200-500ms |
| Storage per Query | ~14KB |

## Cache Statistics

The system internally tracks cache performance:

```python
{
    "memory_entries": 150,
    "disk_entries": 892, 
    "disk_size_mb": 12.4,
    "hit_rate_percent": 67.3,
    "memory_hits": 1205,
    "disk_hits": 343,
    "misses": 587,
    "total_queries": 2135,
    "cache_saves": 587
}
```

## Integration

The cache is automatically integrated into the slide search pipeline:

1. **Transparent Operation**: No changes needed to existing search code
2. **Automatic Initialization**: Cache is created when the SlideProcessingService starts  
3. **Background Maintenance**: Eviction and cleanup happen automatically
4. **Graceful Failure**: System falls back to API calls if cache fails

## Benefits for Users

- **Faster Search Response**: Repeated searches return results much faster
- **Reduced API Costs**: Fewer calls to VoyageAI API
- **Better User Experience**: Snappier interface, especially for common queries
- **Offline Resilience**: Cached queries work even during API outages

## Maintenance

The cache requires no manual maintenance:

- **Automatic Cleanup**: Old entries are removed automatically
- **Self-Healing**: Invalid cache entries are detected and removed
- **Size Management**: Automatic eviction prevents unlimited growth
- **Graceful Restart**: Cache persists across application restarts

## Technical Notes

- Cache keys are based on normalized query text, not embeddings
- Thread-safe for concurrent access from multiple search requests
- Uses efficient binary serialization (pickle) for storage
- Implements proper file locking on disk operations
- Handles edge cases like corrupted cache files gracefully

---

This caching system provides significant performance improvements for SIFFS users while remaining completely transparent and maintenance-free.
