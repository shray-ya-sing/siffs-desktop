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
import { watch, FSWatcher } from 'chokidar';
import { BrowserWindow } from 'electron';
import * as path from 'path';
import * as fs from 'fs';

export interface FileChangeEvent {
  type: 'add' | 'change' | 'unlink' | 'addDir' | 'unlinkDir';
  filePath: string;
  relativePath: string;
  stats?: fs.Stats;
}

export class FileWatcherService {
  private watcher: FSWatcher | null = null;
  private watchedPath: string | null = null;
  private mainWindow: BrowserWindow | null = null;
  private isWatching = false;

  constructor(mainWindow: BrowserWindow) {
    this.mainWindow = mainWindow;
  }

  /**
   * Start watching a directory for file changes
   * @param directoryPath - Absolute path to the directory to watch
   */
  public startWatching(directoryPath: string): void {
    // Stop any existing watcher
    this.stopWatching();

    try {
      // Validate that the path exists and is a directory
      if (!fs.existsSync(directoryPath)) {
        console.error(`FileWatcher: Directory does not exist: ${directoryPath}`);
        return;
      }

      const stats = fs.statSync(directoryPath);
      if (!stats.isDirectory()) {
        console.error(`FileWatcher: Path is not a directory: ${directoryPath}`);
        return;
      }

      this.watchedPath = directoryPath;
      
      // Create watcher with appropriate options
      this.watcher = watch(directoryPath, {
        persistent: true,
        ignoreInitial: true, // Don't emit events for existing files on startup
        followSymlinks: true,
        depth: undefined, // Watch all subdirectories
        awaitWriteFinish: {
          stabilityThreshold: 100, // Wait for file write to stabilize
          pollInterval: 50
        },
        ignored: [
          // Ignore common system and temporary files
          /(^|[\/\\])\../, // Hidden files (starting with .)
          /node_modules/,
          /\.git/,
          /\.vs/,
          /\.vscode/,
          /bin/,
          /obj/,
          /Debug/,
          /Release/,
          /\.tmp$/,
          /~\$/,
          /\.lock$/,
          /\.log$/,
          /Thumbs\.db$/,
          /\.DS_Store$/
        ]
      });

      // Set up event handlers
      this.setupEventHandlers();
      this.isWatching = true;

      console.log(`FileWatcher: Started watching directory: ${directoryPath}`);
      
      // Notify renderer that watching has started
      this.sendToRenderer('file-watcher-started', { watchedPath: directoryPath });

    } catch (error) {
      console.error('FileWatcher: Failed to start watching:', error);
      this.sendToRenderer('file-watcher-error', { 
        error: error instanceof Error ? error.message : 'Unknown error',
        watchedPath: directoryPath
      });
    }
  }

  /**
   * Stop watching the current directory
   */
  public stopWatching(): void {
    if (this.watcher) {
      try {
        this.watcher.close();
        console.log(`FileWatcher: Stopped watching directory: ${this.watchedPath}`);
        
        // Notify renderer that watching has stopped
        this.sendToRenderer('file-watcher-stopped', { watchedPath: this.watchedPath });
        
      } catch (error) {
        console.error('FileWatcher: Error stopping watcher:', error);
      }
      
      this.watcher = null;
    }
    
    this.watchedPath = null;
    this.isWatching = false;
  }

  /**
   * Get the currently watched path
   */
  public getWatchedPath(): string | null {
    return this.watchedPath;
  }

  /**
   * Check if currently watching a directory
   */
  public getIsWatching(): boolean {
    return this.isWatching;
  }

  /**
   * Set up event handlers for the file watcher
   */
  private setupEventHandlers(): void {
    if (!this.watcher || !this.watchedPath) return;

    const basePath = this.watchedPath;

    // File added
    this.watcher.on('add', (filePath: string, stats?: fs.Stats) => {
      const relativePath = path.relative(basePath, filePath);
      console.log(`FileWatcher: File added: ${relativePath}`);
      
      this.sendFileChangeEvent({
        type: 'add',
        filePath,
        relativePath: relativePath.replace(/\\/g, '/'), // Normalize path separators
        stats
      });
    });

    // File changed
    this.watcher.on('change', (filePath: string, stats?: fs.Stats) => {
      const relativePath = path.relative(basePath, filePath);
      console.log(`FileWatcher: File changed: ${relativePath}`);
      
      this.sendFileChangeEvent({
        type: 'change',
        filePath,
        relativePath: relativePath.replace(/\\/g, '/'),
        stats
      });
    });

    // File removed
    this.watcher.on('unlink', (filePath: string) => {
      const relativePath = path.relative(basePath, filePath);
      console.log(`FileWatcher: File removed: ${relativePath}`);
      
      this.sendFileChangeEvent({
        type: 'unlink',
        filePath,
        relativePath: relativePath.replace(/\\/g, '/')
      });
    });

    // Directory added
    this.watcher.on('addDir', (dirPath: string, stats?: fs.Stats) => {
      const relativePath = path.relative(basePath, dirPath);
      console.log(`FileWatcher: Directory added: ${relativePath}`);
      
      this.sendFileChangeEvent({
        type: 'addDir',
        filePath: dirPath,
        relativePath: relativePath.replace(/\\/g, '/'),
        stats
      });
    });

    // Directory removed
    this.watcher.on('unlinkDir', (dirPath: string) => {
      const relativePath = path.relative(basePath, dirPath);
      console.log(`FileWatcher: Directory removed: ${relativePath}`);
      
      this.sendFileChangeEvent({
        type: 'unlinkDir',
        filePath: dirPath,
        relativePath: relativePath.replace(/\\/g, '/')
      });
    });

    // Error handling
    this.watcher.on('error', (err: unknown) => {
      const error = err instanceof Error ? err : new Error(String(err));
      console.error('FileWatcher: Watcher error:', error);
      this.sendToRenderer('file-watcher-error', { 
        error: error.message,
        watchedPath: this.watchedPath
      });
    });

    // Ready event
    this.watcher.on('ready', () => {
      console.log('FileWatcher: Initial scan complete. Ready for changes.');
      this.sendToRenderer('file-watcher-ready', { watchedPath: this.watchedPath });
    });
  }

  /**
   * Send file change event to renderer process
   */
  private sendFileChangeEvent(event: FileChangeEvent): void {
    this.sendToRenderer('file-change', event);
  }

  /**
   * Send message to renderer process
   */
  private sendToRenderer(channel: string, data: any): void {
    console.log(`FileWatcher: Sending IPC message to renderer - Channel: ${channel}, Data:`, data);
    
    if (!this.mainWindow) {
      console.error('FileWatcher: Cannot send to renderer - mainWindow is null');
      return;
    }
    
    if (this.mainWindow.isDestroyed()) {
      console.error('FileWatcher: Cannot send to renderer - mainWindow is destroyed');
      return;
    }
    
    try {
      this.mainWindow.webContents.send(channel, data);
      console.log(`FileWatcher: Successfully sent IPC message - Channel: ${channel}`);
    } catch (error) {
      console.error(`FileWatcher: Error sending IPC message - Channel: ${channel}, Error:`, error);
    }
  }

  /**
   * Clean up resources
   */
  public destroy(): void {
    this.stopWatching();
    this.mainWindow = null;
  }
}
