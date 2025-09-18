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
import { FileChangeEvent } from './fileWatcherService';
import { webSocketService } from './websocket/websocket.service';
import { cacheInvalidationService, FileProcessingContext } from './cacheInvalidationService';
import { v4 as uuidv4 } from 'uuid';

export interface ProcessingQueue {
  filePath: string;
  requestId: string;
  timestamp: number;
  type: 'add' | 'change';
}

export class FileProcessingService {
  private processingQueue: ProcessingQueue[] = [];
  private isProcessing = false;
  private processingContext: FileProcessingContext | null = null;
  private processingDelay = 2000; // Wait 2 seconds before processing to avoid rapid fire events

  /**
   * Set the processing context (workspace info)
   */
  setProcessingContext(context: FileProcessingContext): void {
    this.processingContext = context;
    console.log('FileProcessing: Context set:', context);
  }

  /**
   * Handle file change events and queue for processing
   */
  handleFileChange(event: FileChangeEvent): void {
    if (!this.processingContext) {
      console.warn('FileProcessing: No processing context set, skipping file processing');
      return;
    }

    console.log('FileProcessing: Handling file change:', event);

    // Handle cache invalidation first
    cacheInvalidationService.handleFileChange(event);

    // Check if this is a file we should process
    if (!this.shouldProcessFile(event)) {
      console.log('FileProcessing: Skipping processing for:', event.relativePath);
      return;
    }

    switch (event.type) {
      case 'add':
        this.queueFileForProcessing(event, 'add');
        break;
      case 'change':
        this.queueFileForProcessing(event, 'change');
        break;
      case 'unlink':
        this.handleFileDeleted(event);
        break;
      case 'unlinkDir':
        this.handleDirectoryDeleted(event);
        break;
    }
  }

  /**
   * Check if a file should be processed
   */
  private shouldProcessFile(event: FileChangeEvent): boolean {
    // Only process files, not directories
    if (event.type === 'addDir' || event.type === 'unlinkDir') {
      return false;
    }

    // Check supported file extensions
    const supportedExtensions = ['.xlsx', '.xls', '.pptx', '.ppt', '.pdf', '.docx', '.doc'];
    const extension = event.relativePath.toLowerCase().substring(event.relativePath.lastIndexOf('.'));
    
    return supportedExtensions.includes(extension);
  }

  /**
   * Queue a file for processing
   */
  private queueFileForProcessing(event: FileChangeEvent, type: 'add' | 'change'): void {
    const requestId = uuidv4();
    
    // Remove any existing queue entry for this file to avoid duplicates
    this.processingQueue = this.processingQueue.filter(
      item => item.filePath !== event.relativePath
    );

    // Add to queue
    this.processingQueue.push({
      filePath: event.relativePath,
      requestId,
      timestamp: Date.now(),
      type
    });

    console.log(`FileProcessing: Queued ${type} for processing:`, event.relativePath);

    // Start processing if not already running
    this.startProcessingQueue();
  }

  /**
   * Start processing the queue
   */
  private async startProcessingQueue(): Promise<void> {
    if (this.isProcessing || this.processingQueue.length === 0) {
      return;
    }

    this.isProcessing = true;
    console.log('FileProcessing: Starting queue processing...');

    while (this.processingQueue.length > 0) {
      // Wait for the processing delay to handle rapid file changes
      await new Promise(resolve => setTimeout(resolve, this.processingDelay));

      // Get the next item to process
      const item = this.processingQueue.shift();
      if (!item) continue;

      // Check if the file still exists and hasn't been modified recently
      const now = Date.now();
      if (now - item.timestamp < this.processingDelay) {
        // File was modified too recently, re-queue it
        this.processingQueue.push({ ...item, timestamp: now });
        continue;
      }

      await this.processFile(item);
    }

    this.isProcessing = false;
    console.log('FileProcessing: Queue processing completed');
  }

  /**
   * Process a single file
   */
  private async processFile(item: ProcessingQueue): Promise<void> {
    if (!this.processingContext) {
      console.error('FileProcessing: No processing context available');
      return;
    }

    console.log(`FileProcessing: Processing ${item.type} for file:`, item.filePath);

    try {
      // Get file content from main process
      const electron = (window as any).electron;
      if (!electron?.ipcRenderer) {
        throw new Error('Electron IPC not available');
      }

      const fullPath = `${this.processingContext.workspacePath}/${item.filePath}`;
      const fileResult = await electron.ipcRenderer.invoke('fs:read-file', fullPath);

      if (!fileResult.success) {
        throw new Error(fileResult.error || 'Failed to read file');
      }

      const base64Content = fileResult.content;

      // Determine file type and send appropriate extraction request
      const fileName = item.filePath.split('/').pop() || '';
      const isExcelFile = fileName.endsWith('.xlsx') || fileName.endsWith('.xls');
      const isPowerPointFile = fileName.endsWith('.pptx') || fileName.endsWith('.ppt');
      const isPdfFile = fileName.endsWith('.pdf');
      const isWordFile = fileName.endsWith('.docx') || fileName.endsWith('.doc');

      const messageData = {
        client_id: this.processingContext.clientId,
        request_id: item.requestId,
        file_path: `${this.processingContext.workspaceName || 'workspace'}/${item.filePath}`,
        file_content: base64Content
      };

      console.log('FileProcessing: Sending file for extraction:', {
        ...messageData,
        file_content: `[${base64Content.length} chars]` // Don't log actual content
      });

      if (isExcelFile) {
        webSocketService.emit('EXTRACT_METADATA', messageData);
      } else if (isPowerPointFile) {
        webSocketService.emit('EXTRACT_POWERPOINT_METADATA', messageData);
      } else if (isPdfFile) {
        webSocketService.emit('EXTRACT_PDF_CONTENT', {
          ...messageData,
          include_images: true,
          include_tables: true,
          include_forms: true,
          ocr_images: false
        });
      } else if (isWordFile) {
        webSocketService.emit('EXTRACT_WORD_METADATA', messageData);
      }

      console.log(`FileProcessing: Successfully queued ${fileName} for extraction`);

    } catch (error) {
      console.error(`FileProcessing: Error processing file ${item.filePath}:`, error);
    }
  }

  /**
   * Handle file deletion
   */
  private handleFileDeleted(event: FileChangeEvent): void {
    console.log('FileProcessing: File deleted:', event.relativePath);
    
    // Remove from processing queue if it exists
    this.processingQueue = this.processingQueue.filter(
      item => item.filePath !== event.relativePath
    );

    // TODO: Send deletion notification to backend if needed
    // webSocketService.emit('FILE_DELETED', {
    //   client_id: this.processingContext?.clientId,
    //   file_path: event.relativePath
    // });
  }

  /**
   * Handle directory deletion
   */
  private handleDirectoryDeleted(event: FileChangeEvent): void {
    console.log('FileProcessing: Directory deleted:', event.relativePath);
    
    // Remove all files in this directory from processing queue
    this.processingQueue = this.processingQueue.filter(
      item => !item.filePath.startsWith(event.relativePath + '/')
    );
  }

  /**
   * Get current queue status
   */
  getQueueStatus(): {
    queueLength: number;
    isProcessing: boolean;
    nextProcessing?: ProcessingQueue;
  } {
    return {
      queueLength: this.processingQueue.length,
      isProcessing: this.isProcessing,
      nextProcessing: this.processingQueue[0]
    };
  }

  /**
   * Clear the processing queue
   */
  clearQueue(): void {
    this.processingQueue = [];
    console.log('FileProcessing: Queue cleared');
  }

  /**
   * Set processing delay
   */
  setProcessingDelay(delay: number): void {
    this.processingDelay = delay;
    console.log('FileProcessing: Processing delay set to:', delay);
  }
}

// Create singleton instance
export const fileProcessingService = new FileProcessingService();
