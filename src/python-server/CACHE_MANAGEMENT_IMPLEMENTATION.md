# Cache Management System Implementation

## Problem Statement

The bug in the app was that when files were renamed, deleted, or moved, the changes reflected in the file system and UI but not in the `files_mappings.json` cache file. The cache file would get new entries when files were changed and re-extracted, but old entries were never removed. This caused the workspace caches to accumulate stale entries, misleading the LLM and agent.

## Solution Overview

We implemented a comprehensive cache management system that addresses this issue by:

1. **Automated cleanup** of stale cache entries
2. **File system monitoring** to detect file changes
3. **Centralized cache management** with a robust API
4. **Integration with existing orchestrators** 

## Components Implemented

### 1. CacheManager (`cache_management/cache_manager.py`)
- **Purpose**: Core cache management logic
- **Key Features**:
  - Loads and saves file mappings
  - Detects and removes stale mappings
  - Handles file moves, deletions, and renames
  - Cleans up associated metadata cache files
  - Provides cache statistics

### 2. FileWatcher (`cache_management/file_watcher.py`)
- **Purpose**: Monitors file system changes
- **Key Features**:
  - Uses `watchdog` library for file system monitoring
  - Debounces events to avoid rapid-fire processing
  - Handles file creation, deletion, modification, and moves
  - Monitors common workspace directories
  - Automatically updates cache when files change

### 3. CacheService (`cache_management/cache_service.py`)
- **Purpose**: High-level service that coordinates cache management
- **Key Features**:
  - Integrates CacheManager and FileWatcher
  - Manages application lifecycle (startup/shutdown)
  - Provides unified API for cache operations
  - Handles workspace path management

### 4. Updated Orchestrators
Updated all orchestrators to use the new cache management system:
- **Excel Orchestrator** (`excel/orchestration/excel_orchestrator.py`)
- **PDF Orchestrator** (`pdf/orchestration/pdf_orchestrator.py`)
- **PowerPoint Orchestrator** (`powerpoint/orchestration/powerpoint_orchestrator.py`)
- **Word Orchestrator** (`word/orchestration/word_orchestrator.py`)

### 5. API Endpoints (`api/routes/cache.py`)
Added new cache management endpoints:
- `POST /clear-cache` - Clear all cache
- `POST /cleanup-cache` - Remove stale entries
- `GET /cache-stats` - Get cache statistics
- `POST /restart-file-watcher` - Restart file monitoring

### 6. Application Integration (`app.py`)
- Integrated cache service into application startup
- Added proper shutdown handling
- Automatic cache cleanup on startup

## Key Improvements

### Before the Fix
- ✗ Old file paths remained in `files_mappings.json` indefinitely
- ✗ Stale metadata accumulated in `metadata/__cache`
- ✗ No automatic cleanup of invalid cache entries
- ✗ Manual cache clearing was the only option

### After the Fix
- ✅ Automatic cleanup of stale cache entries
- ✅ Real-time file system monitoring
- ✅ Proper handling of file moves, renames, and deletions
- ✅ Centralized cache management with comprehensive API
- ✅ Integration with application lifecycle
- ✅ Robust error handling and logging

## File System Events Handled

1. **File Creation**: Detected and logged (handled by normal upload flow)
2. **File Deletion**: Removes mapping and associated cache files
3. **File Modification**: Logged (triggers re-extraction through normal flow)
4. **File Move/Rename**: Updates mappings to reflect new path

## Cache Cleanup Process

1. **Stale Detection**: Identifies files that no longer exist in the file system
2. **Mapping Cleanup**: Removes stale entries from `files_mappings.json`
3. **Metadata Cleanup**: Removes associated cache files from `metadata/_cache`
4. **Statistics**: Provides detailed stats about cleanup operations

## API Usage Examples

### Get Cache Statistics
```bash
curl -X GET http://localhost:3001/cache-stats
```

### Cleanup Stale Entries
```bash
curl -X POST http://localhost:3001/cleanup-cache
```

### Clear All Cache
```bash
curl -X POST http://localhost:3001/clear-cache
```

## Configuration

The system monitors these common workspace directories by default:
- `~/Downloads`
- `~/Desktop`
- `~/Documents`
- `~/workspace`
- `~/projects`

Additional paths can be added dynamically through the CacheService API.

## Dependencies Added

- `watchdog` - For file system monitoring

## Testing

A comprehensive test suite (`test_cache_management.py`) validates:
- Cache manager functionality
- File watcher operations  
- Service integration
- Real-world workflow scenarios

All tests pass successfully, confirming the system works as expected.

## Benefits

1. **Automatic Maintenance**: No manual intervention needed for cache cleanup
2. **Real-time Updates**: File system changes are immediately reflected in cache
3. **Improved Performance**: Eliminates processing of stale file references
4. **Better User Experience**: Accurate workspace file listings
5. **Robust Error Handling**: Graceful handling of edge cases
6. **Comprehensive Monitoring**: Detailed logging and statistics

## Future Enhancements

1. **Configurable Watch Paths**: Allow users to specify custom directories
2. **Cache Size Limits**: Implement automatic cleanup based on cache size
3. **Performance Metrics**: Track cache hit rates and processing times
4. **Backup/Restore**: Implement cache backup and restoration capabilities

The cache management system successfully solves the original bug and provides a solid foundation for future enhancements.
