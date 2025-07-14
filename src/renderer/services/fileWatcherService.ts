import { FileItem } from '../hooks/useFileTree';

export interface FileChangeEvent {
  type: 'add' | 'change' | 'unlink' | 'addDir' | 'unlinkDir';
  filePath: string;
  relativePath: string;
  stats?: any;
}

export interface FileWatcherStatus {
  success: boolean;
  watchedPath?: string;
  isWatching?: boolean;
  error?: string;
}

type FileChangeCallback = (event: FileChangeEvent) => void;
type WatcherStatusCallback = (status: { type: 'started' | 'stopped' | 'ready' | 'error'; data: any }) => void;

export class FileWatcherService {
  private fileChangeCallbacks: Set<FileChangeCallback> = new Set();
  private statusCallbacks: Set<WatcherStatusCallback> = new Set();
  private isInitialized = false;

  constructor() {
    this.setupIpcListeners();
  }

  /**
   * Set up IPC listeners for file watcher events from main process
   */
  private setupIpcListeners(): void {
    if (this.isInitialized) return;

    const electron = (window as any).electron;
    if (!electron?.ipcRenderer) {
      console.warn('FileWatcherService: Electron IPC not available');
      return;
    }

    // Listen for file change events
    electron.ipcRenderer.on('file-change', (event: any, data: FileChangeEvent) => {
      console.log('FileWatcher: Received file change event:', data);
      this.notifyFileChangeCallbacks(data);
    });

    // Listen for watcher status events
    electron.ipcRenderer.on('file-watcher-started', (event: any, data: { watchedPath: string }) => {
      console.log('FileWatcher: Watching started for:', data.watchedPath);
      this.notifyStatusCallbacks({ type: 'started', data });
    });

    electron.ipcRenderer.on('file-watcher-stopped', (event: any, data: { watchedPath: string }) => {
      console.log('FileWatcher: Watching stopped for:', data.watchedPath);
      this.notifyStatusCallbacks({ type: 'stopped', data });
    });

    electron.ipcRenderer.on('file-watcher-ready', (event: any, data: { watchedPath: string }) => {
      console.log('FileWatcher: Initial scan complete for:', data.watchedPath);
      this.notifyStatusCallbacks({ type: 'ready', data });
    });

    electron.ipcRenderer.on('file-watcher-error', (event: any, data: { error: string; watchedPath?: string }) => {
      console.error('FileWatcher: Error:', data.error);
      const sanitizedData = { ...data };
      if (!data.watchedPath) delete sanitizedData.watchedPath;
      this.notifyStatusCallbacks({ type: 'error', data: sanitizedData });
    });

    this.isInitialized = true;
  }

  /**
   * Start watching a directory
   * @param directoryPath - Absolute path to the directory to watch
   */
  async startWatching(directoryPath: string): Promise<FileWatcherStatus> {
    const electron = (window as any).electron;
    if (!electron?.ipcRenderer) {
      return { success: false, error: 'Electron IPC not available' };
    }

    try {
      const result = await electron.ipcRenderer.invoke('file-watcher:start-watching', directoryPath);
      console.log('FileWatcher: Start watching result:', result);
      return result;
    } catch (error) {
      console.error('FileWatcher: Failed to start watching:', error);
      return { 
        success: false, 
        error: error instanceof Error ? error.message : 'Unknown error' 
      };
    }
  }

  /**
   * Stop watching the current directory
   */
  async stopWatching(): Promise<FileWatcherStatus> {
    const electron = (window as any).electron;
    if (!electron?.ipcRenderer) {
      return { success: false, error: 'Electron IPC not available' };
    }

    try {
      const result = await electron.ipcRenderer.invoke('file-watcher:stop-watching');
      console.log('FileWatcher: Stop watching result:', result);
      return result;
    } catch (error) {
      console.error('FileWatcher: Failed to stop watching:', error);
      return { 
        success: false, 
        error: error instanceof Error ? error.message : 'Unknown error' 
      };
    }
  }

  /**
   * Get the current watched path and status
   */
  async getWatchedPath(): Promise<FileWatcherStatus> {
    const electron = (window as any).electron;
    if (!electron?.ipcRenderer) {
      return { success: false, error: 'Electron IPC not available' };
    }

    try {
      const result = await electron.ipcRenderer.invoke('file-watcher:get-watched-path');
      console.log('FileWatcher: Get watched path result:', result);
      return result;
    } catch (error) {
      console.error('FileWatcher: Failed to get watched path:', error);
      return { 
        success: false, 
        error: error instanceof Error ? error.message : 'Unknown error' 
      };
    }
  }

  /**
   * Register a callback for file change events
   */
  onFileChange(callback: FileChangeCallback): () => void {
    this.fileChangeCallbacks.add(callback);
    
    // Return unsubscribe function
    return () => {
      this.fileChangeCallbacks.delete(callback);
    };
  }

  /**
   * Register a callback for watcher status events
   */
  onStatusChange(callback: WatcherStatusCallback): () => void {
    this.statusCallbacks.add(callback);
    
    // Return unsubscribe function
    return () => {
      this.statusCallbacks.delete(callback);
    };
  }

  /**
   * Notify all file change callbacks
   */
  private notifyFileChangeCallbacks(event: FileChangeEvent): void {
    this.fileChangeCallbacks.forEach(callback => {
      try {
        callback(event);
      } catch (error) {
        console.error('FileWatcher: Error in file change callback:', error);
      }
    });
  }

  /**
   * Notify all status callbacks
   */
  private notifyStatusCallbacks(status: { type: 'started' | 'stopped' | 'ready' | 'error'; data: any }): void {
    this.statusCallbacks.forEach(callback => {
      try {
        callback(status);
      } catch (error) {
        console.error('FileWatcher: Error in status callback:', error);
      }
    });
  }

  /**
   * Utility function to convert file change events to FileItem format
   */
  static fileChangeEventToFileItem(event: FileChangeEvent, basePath: string = ''): FileItem {
    const isDirectory = event.type === 'addDir' || event.type === 'unlinkDir';
    
    return {
      name: event.relativePath.split('/').pop() || '',
      path: event.relativePath,
      isDirectory
    };
  }

  /**
   * Utility function to check if a file should be processed based on supported extensions
   */
  static shouldProcessFile(filePath: string): boolean {
    const supportedExtensions = [
      '.xlsx', '.xls',  // Excel files
      '.pptx', '.ppt',  // PowerPoint files
      '.pdf',           // PDF files
      '.docx', '.doc'   // Word files
    ];

    const extension = filePath.toLowerCase().substring(filePath.lastIndexOf('.'));
    return supportedExtensions.includes(extension);
  }

  /**
   * Clean up resources
   */
  destroy(): void {
    this.fileChangeCallbacks.clear();
    this.statusCallbacks.clear();
    
    // Note: We don't remove IPC listeners here because they're global to the renderer process
    // and might be used by other instances
  }
}

// Create a singleton instance
export const fileWatcherService = new FileWatcherService();
