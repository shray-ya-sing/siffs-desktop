import { FileChangeEvent } from './fileWatcherService';
import { webSocketService } from './websocket/websocket.service';
import { v4 as uuidv4 } from 'uuid';

export interface CacheInvalidationOptions {
  forceRefresh?: boolean;
  clearAll?: boolean;
}

export interface FileProcessingContext {
  workspacePath: string;
  clientId: string;
  workspaceName?: string;
}

export class CacheInvalidationService {
  private pendingInvalidations: Set<string> = new Set();
  private invalidationCallbacks: Map<string, (() => void)[]> = new Map();

  /**
   * Handle file change events and determine what needs to be invalidated
   */
  handleFileChange(event: FileChangeEvent): void {
    console.log('CacheInvalidation: Processing file change:', event);

    const shouldInvalidate = this.shouldInvalidateCache(event);
    if (!shouldInvalidate) {
      console.log('CacheInvalidation: Skipping cache invalidation for:', event.relativePath);
      return;
    }

    switch (event.type) {
      case 'change':
        this.invalidateFileCache(event.relativePath);
        break;
      case 'unlink':
        this.removeFileCache(event.relativePath);
        break;
      case 'add':
        // For new files, we don't need to invalidate existing cache
        // but we might want to trigger processing if it's a supported file
        console.log('CacheInvalidation: New file added:', event.relativePath);
        break;
      case 'unlinkDir':
        this.invalidateDirectoryCache(event.relativePath);
        break;
    }
  }

  /**
   * Determine if a file change should trigger cache invalidation
   */
  private shouldInvalidateCache(event: FileChangeEvent): boolean {
    const supportedExtensions = ['.xlsx', '.xls', '.pptx', '.ppt', '.pdf', '.docx', '.doc'];
    const extension = event.relativePath.toLowerCase().substring(event.relativePath.lastIndexOf('.'));
    
    return supportedExtensions.includes(extension);
  }

  /**
   * Invalidate cache for a specific file
   */
  invalidateFileCache(filePath: string): void {
    console.log('CacheInvalidation: Invalidating cache for file:', filePath);
    
    // Add to pending invalidations
    this.pendingInvalidations.add(filePath);
    
    // Trigger callbacks for this file
    const callbacks = this.invalidationCallbacks.get(filePath) || [];
    callbacks.forEach(callback => {
      try {
        callback();
      } catch (error) {
        console.error('CacheInvalidation: Error in callback:', error);
      }
    });

    // Clear the pending invalidation after processing
    setTimeout(() => {
      this.pendingInvalidations.delete(filePath);
    }, 1000);
  }

  /**
   * Remove cache entries for a deleted file
   */
  removeFileCache(filePath: string): void {
    console.log('CacheInvalidation: Removing cache for deleted file:', filePath);
    
    // TODO: Implement actual cache removal logic
    // This would need to interact with the Python backend to clear cached metadata
    this.sendCacheInvalidationToBackend(filePath, { clearAll: true });
  }

  /**
   * Invalidate cache for all files in a directory
   */
  invalidateDirectoryCache(dirPath: string): void {
    console.log('CacheInvalidation: Invalidating cache for directory:', dirPath);
    
    // Find all cached files in this directory
    const affectedFiles = Array.from(this.invalidationCallbacks.keys())
      .filter(path => path.startsWith(dirPath + '/'));
    
    affectedFiles.forEach(filePath => this.invalidateFileCache(filePath));
  }

  /**
   * Register a callback for cache invalidation events
   */
  onFileInvalidated(filePath: string, callback: () => void): () => void {
    if (!this.invalidationCallbacks.has(filePath)) {
      this.invalidationCallbacks.set(filePath, []);
    }
    
    this.invalidationCallbacks.get(filePath)!.push(callback);
    
    // Return unsubscribe function
    return () => {
      const callbacks = this.invalidationCallbacks.get(filePath);
      if (callbacks) {
        const index = callbacks.indexOf(callback);
        if (index > -1) {
          callbacks.splice(index, 1);
        }
        
        if (callbacks.length === 0) {
          this.invalidationCallbacks.delete(filePath);
        }
      }
    };
  }

  /**
   * Check if a file has pending invalidations
   */
  hasPendingInvalidation(filePath: string): boolean {
    return this.pendingInvalidations.has(filePath);
  }

  /**
   * Get all files with pending invalidations
   */
  getPendingInvalidations(): string[] {
    return Array.from(this.pendingInvalidations);
  }

  /**
   * Send cache invalidation request to backend
   */
  private sendCacheInvalidationToBackend(filePath: string, options: CacheInvalidationOptions = {}): void {
    // TODO: Implement backend communication for cache invalidation
    // This would send a message to the Python backend to clear/refresh cache entries
    console.log('CacheInvalidation: Would send to backend:', {
      filePath,
      options,
      action: 'invalidate_cache'
    });
    
    // Example implementation:
    // webSocketService.emit('INVALIDATE_CACHE', {
    //   filePath,
    //   forceRefresh: options.forceRefresh || false,
    //   clearAll: options.clearAll || false
    // });
  }

  /**
   * Manually trigger cache refresh for a file
   */
  async refreshFileCache(filePath: string): Promise<void> {
    console.log('CacheInvalidation: Manually refreshing cache for:', filePath);
    
    this.sendCacheInvalidationToBackend(filePath, { forceRefresh: true });
    this.invalidateFileCache(filePath);
  }

  /**
   * Clear all invalidation tracking
   */
  clearAll(): void {
    this.pendingInvalidations.clear();
    this.invalidationCallbacks.clear();
  }

  /**
   * Get statistics about cache invalidation
   */
  getStats(): {
    pendingCount: number;
    trackedFiles: number;
    totalCallbacks: number;
  } {
    return {
      pendingCount: this.pendingInvalidations.size,
      trackedFiles: this.invalidationCallbacks.size,
      totalCallbacks: Array.from(this.invalidationCallbacks.values())
        .reduce((sum, callbacks) => sum + callbacks.length, 0)
    };
  }
}

// Create singleton instance
export const cacheInvalidationService = new CacheInvalidationService();
