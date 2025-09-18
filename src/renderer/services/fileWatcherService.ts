/*
 * Siffs - Fast File Search Desktop Application
 * Copyright (C) 2025  Siffs
 * 
 * Contact: github.suggest277@passinbox.com
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */
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
    console.log('FileWatcherService: Initializing IPC listeners');
    if (this.isInitialized) {
      console.warn('FileWatcherService: IPC listeners already initialized');
      return;
    }

    const electron = (window as any).electron;
    if (!electron?.ipcRenderer) {
      console.warn('FileWatcherService: Electron IPC not available');
      return;
    }

    // Listen for file change events
    electron.ipcRenderer.on('file-change', (event: any, data: FileChangeEvent) => {
      console.log('FileWatcher: Received file change event - Event:', event, 'Data:', data);
      try {
        if (!data) {
          console.error('FileWatcher: Received null/undefined data for file-change event');
          return;
        }
        this.notifyFileChangeCallbacks(data);
      } catch (error) {
        console.error('FileWatcher: Error handling file-change event:', error, 'Data:', data);
      }
    });

    // Listen for watcher status events
    electron.ipcRenderer.on('file-watcher-started', (event: any, data: { watchedPath: string }) => {
      console.log('FileWatcher: Received file-watcher-started - Event:', event, 'Data:', data);
      try {
        // The data is actually in the event object, not the data parameter
        const actualData = data || event;
        if (!actualData || !actualData.watchedPath) {
          console.error('FileWatcher: Received invalid data for file-watcher-started event. Event:', event, 'Data:', data);
          return;
        }
        console.log('FileWatcher: Watching started for:', actualData.watchedPath);
        this.notifyStatusCallbacks({ type: 'started', data: actualData });
      } catch (error) {
        console.error('FileWatcher: Error handling file-watcher-started event:', error, 'Event:', event, 'Data:', data);
      }
    });

    electron.ipcRenderer.on('file-watcher-stopped', (event: any, data: { watchedPath: string }) => {
      console.log('FileWatcher: Received file-watcher-stopped - Event:', event, 'Data:', data);
      try {
        // The data is actually in the event object, not the data parameter
        const actualData = data || event;
        if (!actualData) {
          console.error('FileWatcher: Received null/undefined data for file-watcher-stopped event. Event:', event, 'Data:', data);
          return;
        }
        console.log('FileWatcher: Watching stopped for:', actualData.watchedPath || 'unknown path');
        this.notifyStatusCallbacks({ type: 'stopped', data: actualData });
      } catch (error) {
        console.error('FileWatcher: Error handling file-watcher-stopped event:', error, 'Event:', event, 'Data:', data);
      }
    });

    electron.ipcRenderer.on('file-watcher-ready', (event: any, data: { watchedPath: string }) => {
      console.log('FileWatcher: Received file-watcher-ready - Event:', event, 'Data:', data);
      try {
        // The data is actually in the event object, not the data parameter
        const actualData = data || event;
        if (!actualData) {
          console.error('FileWatcher: Received null/undefined data for file-watcher-ready event. Event:', event, 'Data:', data);
          return;
        }
        console.log('FileWatcher: Initial scan complete for:', actualData.watchedPath || 'unknown path');
        this.notifyStatusCallbacks({ type: 'ready', data: actualData });
      } catch (error) {
        console.error('FileWatcher: Error handling file-watcher-ready event:', error, 'Event:', event, 'Data:', data);
      }
    });

    electron.ipcRenderer.on('file-watcher-error', (event: any, data: { error: string; watchedPath?: string }) => {
      console.log('FileWatcher: Received file-watcher-error - Event:', event, 'Data:', data);
      try {
        // The data is actually in the event object, not the data parameter
        const actualData = data || event;
        if (!actualData) {
          console.error('FileWatcher: Received null/undefined data for file-watcher-error event. Event:', event, 'Data:', data);
          return;
        }
        console.error('FileWatcher: Error:', actualData.error || 'Unknown error');
        const sanitizedData = { ...actualData };
        if (!actualData.watchedPath) delete sanitizedData.watchedPath;
        this.notifyStatusCallbacks({ type: 'error', data: sanitizedData });
      } catch (error) {
        console.error('FileWatcher: Error handling file-watcher-error event:', error, 'Event:', event, 'Data:', data);
      }
    });

    this.isInitialized = true;
    console.log('FileWatcherService: IPC listeners set up successfully');
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
