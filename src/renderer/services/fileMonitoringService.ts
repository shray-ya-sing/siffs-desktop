import { fileWatcherService, FileWatcherService, FileChangeEvent } from './fileWatcherService';
import { cacheInvalidationService } from './cacheInvalidationService';
import { FileItem } from '../hooks/useFileTree';

export interface FileMonitoringConfig {
  enableCacheInvalidation: boolean;
  enableAutoProcessing: boolean;
  debounceMs: number;
}

type FileTreeUpdateCallback = (update: FileTreeUpdate) => void;
type FileProcessingCallback = (file: FileItem) => void;

export interface FileTreeUpdate {
  type: 'add' | 'remove' | 'change';
  file: FileItem;
  path: string;
}

export class FileMonitoringService {
  private config: FileMonitoringConfig = {
    enableCacheInvalidation: true,
    enableAutoProcessing: false,
    debounceMs: 500
  };

  private fileTreeCallbacks: Set<FileTreeUpdateCallback> = new Set();
  private processingCallbacks: Set<FileProcessingCallback> = new Set();
  private isMonitoring = false;
  private currentWatchPath: string | null = null;
  private debounceTimers: Map<string, NodeJS.Timeout> = new Map();

  constructor(config?: Partial<FileMonitoringConfig>) {
    if (config) {
      this.config = { ...this.config, ...config };
    }
    this.setupFileWatcherListeners();
  }

  /**
   * Start monitoring a directory
   */
  async startMonitoring(directoryPath: string): Promise<{ success: boolean; error?: string }> {
    console.log('FileMonitoring: Starting monitoring for:', directoryPath);

    try {
      // Start the file watcher
      const result = await fileWatcherService.startWatching(directoryPath);
      
      if (result.success) {
        this.isMonitoring = true;
        this.currentWatchPath = directoryPath;
        console.log('FileMonitoring: Successfully started monitoring:', directoryPath);
        return { success: true };
      } else {
        console.error('FileMonitoring: Failed to start file watcher:', result.error);
        return { success: false, error: result.error };
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      console.error('FileMonitoring: Error starting monitoring:', errorMessage);
      return { success: false, error: errorMessage };
    }
  }

  /**
   * Stop monitoring
   */
  async stopMonitoring(): Promise<{ success: boolean; error?: string }> {
    console.log('FileMonitoring: Stopping monitoring');

    try {
      const result = await fileWatcherService.stopWatching();
      
      this.isMonitoring = false;
      this.currentWatchPath = null;
      this.clearDebounceTimers();
      
      if (result.success) {
        console.log('FileMonitoring: Successfully stopped monitoring');
        return { success: true };
      } else {
        console.error('FileMonitoring: Failed to stop file watcher:', result.error);
        return { success: false, error: result.error };
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      console.error('FileMonitoring: Error stopping monitoring:', errorMessage);
      return { success: false, error: errorMessage };
    }
  }

  /**
   * Get current monitoring status
   */
  getStatus(): {
    isMonitoring: boolean;
    watchPath: string | null;
    config: FileMonitoringConfig;
  } {
    return {
      isMonitoring: this.isMonitoring,
      watchPath: this.currentWatchPath,
      config: this.config
    };
  }

  /**
   * Update configuration
   */
  updateConfig(newConfig: Partial<FileMonitoringConfig>): void {
    this.config = { ...this.config, ...newConfig };
    console.log('FileMonitoring: Updated config:', this.config);
  }

  /**
   * Register callback for file tree updates
   */
  onFileTreeUpdate(callback: FileTreeUpdateCallback): () => void {
    this.fileTreeCallbacks.add(callback);
    return () => this.fileTreeCallbacks.delete(callback);
  }

  /**
   * Register callback for file processing requests
   */
  onFileProcessingRequest(callback: FileProcessingCallback): () => void {
    this.processingCallbacks.add(callback);
    return () => this.processingCallbacks.delete(callback);
  }

  /**
   * Setup file watcher event listeners
   */
  private setupFileWatcherListeners(): void {
    fileWatcherService.onFileChange((event: FileChangeEvent) => {
      this.handleFileChange(event);
    });

    fileWatcherService.onStatusChange((status) => {
      console.log('FileMonitoring: Watcher status change:', status);
      
      if (status.type === 'error') {
        this.isMonitoring = false;
        console.error('FileMonitoring: File watcher error, stopping monitoring');
      }
    });
  }

  /**
   * Handle file change events with debouncing
   */
  private handleFileChange(event: FileChangeEvent): void {
    console.log('FileMonitoring: Processing file change:', event);

    // Clear existing debounce timer for this file
    const existingTimer = this.debounceTimers.get(event.relativePath);
    if (existingTimer) {
      clearTimeout(existingTimer);
    }

    // Set new debounce timer
    const timer = setTimeout(() => {
      this.processFileChange(event);
      this.debounceTimers.delete(event.relativePath);
    }, this.config.debounceMs);

    this.debounceTimers.set(event.relativePath, timer);
  }

  /**
   * Process file change after debouncing
   */
  private processFileChange(event: FileChangeEvent): void {
    console.log('FileMonitoring: Processing debounced file change:', event);

    // Handle cache invalidation if enabled
    if (this.config.enableCacheInvalidation) {
      cacheInvalidationService.handleFileChange(event);
    }

    // Convert to FileItem and notify callbacks
    const fileItem = this.eventToFileItem(event);
    const update: FileTreeUpdate = {
      type: this.eventTypeToUpdateType(event.type),
      file: fileItem,
      path: event.relativePath
    };

    this.notifyFileTreeCallbacks(update);

    // Handle auto-processing for new/changed supported files
    if (this.config.enableAutoProcessing && this.shouldAutoProcess(event)) {
      this.notifyProcessingCallbacks(fileItem);
    }
  }

  /**
   * Convert file change event to FileItem
   */
  private eventToFileItem(event: FileChangeEvent): FileItem {
    return {
      name: event.relativePath.split('/').pop() || '',
      path: event.relativePath,
      isDirectory: event.type === 'addDir' || event.type === 'unlinkDir'
    };
  }

  /**
   * Convert event type to update type
   */
  private eventTypeToUpdateType(eventType: FileChangeEvent['type']): FileTreeUpdate['type'] {
    switch (eventType) {
      case 'add':
      case 'addDir':
        return 'add';
      case 'unlink':
      case 'unlinkDir':
        return 'remove';
      case 'change':
        return 'change';
      default:
        return 'change';
    }
  }

  /**
   * Determine if a file should be auto-processed
   */
  private shouldAutoProcess(event: FileChangeEvent): boolean {
    // Only auto-process add and change events for supported files
    if (event.type !== 'add' && event.type !== 'change') {
      return false;
    }

    return FileWatcherService.shouldProcessFile(event.relativePath);
  }

  /**
   * Notify file tree update callbacks
   */
  private notifyFileTreeCallbacks(update: FileTreeUpdate): void {
    this.fileTreeCallbacks.forEach(callback => {
      try {
        callback(update);
      } catch (error) {
        console.error('FileMonitoring: Error in file tree callback:', error);
      }
    });
  }

  /**
   * Notify file processing callbacks
   */
  private notifyProcessingCallbacks(file: FileItem): void {
    this.processingCallbacks.forEach(callback => {
      try {
        callback(file);
      } catch (error) {
        console.error('FileMonitoring: Error in processing callback:', error);
      }
    });
  }

  /**
   * Clear all debounce timers
   */
  private clearDebounceTimers(): void {
    this.debounceTimers.forEach(timer => clearTimeout(timer));
    this.debounceTimers.clear();
  }

  /**
   * Get monitoring statistics
   */
  getStats(): {
    isMonitoring: boolean;
    watchPath: string | null;
    pendingDebounces: number;
    cacheStats: any;
  } {
    return {
      isMonitoring: this.isMonitoring,
      watchPath: this.currentWatchPath,
      pendingDebounces: this.debounceTimers.size,
      cacheStats: cacheInvalidationService.getStats()
    };
  }

  /**
   * Clean up resources
   */
  destroy(): void {
    this.stopMonitoring();
    this.clearDebounceTimers();
    this.fileTreeCallbacks.clear();
    this.processingCallbacks.clear();
    cacheInvalidationService.clearAll();
  }
}

// Create singleton instance
export const fileMonitoringService = new FileMonitoringService();
