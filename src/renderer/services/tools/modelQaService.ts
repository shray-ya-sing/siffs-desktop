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
// src/renderer/services/tools/modelQaService.ts
import qaPipelineService from '../python-api/qaPipelineService';

// Types
interface ChunkInfo {
  chunk_index: number;
  token_count: number;
  sheets: string[];
}

interface ModelQACallbacks {
  onMessage: (message: string) => void;
  onError: (error: string) => void;
  onProcessingChange: (isProcessing: boolean) => void;
  onTypingStart: () => void;
  onTypingEnd: () => void;
  onDataReady: (isReady: boolean) => void;
}

export class ModelQAService {
  private cancelRef: (() => void) | null = null;
  private callbacks: ModelQACallbacks;
  private isDataReady = false;
  private currentWorkbookPath: string | null = null;

  constructor(callbacks: ModelQACallbacks) {
    this.callbacks = callbacks;
  }

  // Process Excel file and store embeddings
  async processExcelFile(filePath: string): Promise<boolean> {
    if (!filePath) {
      this.callbacks.onError('File path is required');
      return false;
    }

    this.currentWorkbookPath = filePath;
    this.callbacks.onProcessingChange(true);
    this.callbacks.onMessage('Processing Excel file...');

    try {
      // Step 1: Extract metadata chunks
      this.callbacks.onMessage('Extracting data from Excel file...');
      const extractRes = await qaPipelineService.extractMetadataChunks(filePath);
      
      if (!extractRes.data.chunks?.length) {
        throw new Error('No data was extracted from the Excel file');
      }

      // Step 2: Compress chunks
      this.callbacks.onMessage('Processing extracted data...');
      const compressRes = await qaPipelineService.compressChunks(extractRes.data.chunks);
      
      if (!compressRes.data.compressed_texts?.length) {
        throw new Error('Failed to process the extracted data');
      }

      // Step 3: Store embeddings
      this.callbacks.onMessage('Storing data for question answering...');
      const storeRes = await qaPipelineService.storeEmbeddings(
        filePath,
        extractRes.data.chunks.map((chunk: any, i: number) => ({
          ...chunk,
          text: compressRes.data.compressed_texts[i] || '',
          markdown: compressRes.data.compressed_markdown_texts[i] || ''
        }))
      );

      if (storeRes.status !== 200) {
        throw new Error('Failed to store embeddings');
      }

      this.isDataReady = true;
      this.callbacks.onDataReady(true);
      this.callbacks.onMessage('✓ Data processing complete! You can now ask questions about your file.');
      return true;

    } catch (error: any) {
      this.callbacks.onError(this.getErrorMessage(error));
      this.isDataReady = false;
      this.callbacks.onDataReady(false);
      return false;
    } finally {
      this.callbacks.onProcessingChange(false);
    }
  }

  // Process a user message
  async processMessage(message: string): Promise<void> {
    if (!this.isDataReady || !this.currentWorkbookPath) {
      this.callbacks.onError('Please process an Excel file first');
      return;
    }

    this.callbacks.onProcessingChange(true);
    this.callbacks.onTypingStart();

    try {
      // Search for relevant chunks
      const searchRes = await qaPipelineService.searchEmbeddings(
        message,
        this.currentWorkbookPath,
        3 // top_k
      );

      if (!searchRes.data.results?.length) {
        this.callbacks.onMessage('No relevant information found to answer your question.');
        return;
      }

      // Stream the answer
      const { cancel } = qaPipelineService.streamAnswer(
        searchRes.data,
        message,
        (chunk, isDone) => {
          if (chunk) {
            this.callbacks.onMessage(chunk);
          }
          if (isDone) {
            this.callbacks.onTypingEnd();
            this.callbacks.onProcessingChange(false);
          }
        },
        (error) => {
          this.callbacks.onError(`Error: ${this.getErrorMessage(error)}`);
          this.callbacks.onTypingEnd();
          this.callbacks.onProcessingChange(false);
        }
      );

      this.cancelRef = cancel;

    } catch (error: any) {
      this.callbacks.onError(this.getErrorMessage(error));
      this.callbacks.onTypingEnd();
      this.callbacks.onProcessingChange(false);
    }
  }

  cancel(): void {
    if (this.cancelRef) {
      this.cancelRef();
      this.cancelRef = null;
    }
  }

  cleanup(): void {
    this.cancel();
    this.isDataReady = false;
    this.currentWorkbookPath = null;
  }

  private getErrorMessage(error: any): string {
    return error?.response?.data?.detail || error?.message || 'An unknown error occurred';
  }
}