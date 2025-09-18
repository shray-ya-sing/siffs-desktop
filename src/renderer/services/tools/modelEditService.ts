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
// src/renderer/services/tools/modelEditService.ts
import modelEditPipelineService from '../python-api/modelEditPipelineService';
import qaPipelineService from '../python-api/qaPipelineService';
import { AcceptEditsResponse, RejectEditsResponse } from '../python-api/modelEditPipelineService';

// Types
interface ChunkInfo {
  chunk_index: number;
  token_count: number;
  sheets: string[];
}

interface ModelEditCallbacks {
  onMessage: (message: string) => void;
  onError: (error: string) => void;
  onProcessingChange: (isProcessing: boolean) => void;
  onTypingStart: () => void;
  onTypingEnd: () => void;
  onDataReady: (isReady: boolean) => void;
  onEditComplete: (result: any) => void;
  onEditsAccepted: (result: AcceptEditsResponse) => void;
  onEditsRejected: (result: RejectEditsResponse) => void;
}

export class ModelEditService {
  private callbacks: ModelEditCallbacks;
  private isDataReady = false;
  private currentWorkbookPath: string | null = null;
  private pendingEditIds: string[] = [];

  private storePendingEdits(editResult: any): void {
    if (editResult?.request_pending_edits?.length) {
      this.pendingEditIds = editResult.request_pending_edits
        .map((edit: any) => edit.edit_id)
        .filter(Boolean);
      this.callbacks.onMessage(`✓ ${this.pendingEditIds.length} edits pending acceptance`);
    }
  }

  constructor(callbacks: ModelEditCallbacks) {
    this.callbacks = callbacks;
  }

  // Call this to accept all pending edits
  async acceptPendingEdits(): Promise<void> {
    if (!this.pendingEditIds.length) {
      this.callbacks.onMessage('No pending edits to accept');
      return;
    }

    try {
      this.callbacks.onMessage('Accepting edits...');
      const result = await modelEditPipelineService.acceptEdits(this.pendingEditIds);
      
      if (result.success) {
        this.callbacks.onMessage(`✓ Accepted ${result.accepted_count} edits`);
        this.pendingEditIds = []; // Clear accepted edits
      } else {
        throw new Error('Failed to accept some edits');
      }
      
      this.callbacks.onEditsAccepted(result);
    } catch (error: any) {
      const errorMessage = typeof error === 'string' ? error : 
                         error?.message || 'Failed to accept edits';
      this.callbacks.onError(errorMessage);
      throw error;
    }
  }


  // Call this to reject all pending edits
  async rejectPendingEdits(): Promise<void> {
    if (!this.pendingEditIds.length) {
      this.callbacks.onMessage('No pending edits to reject');
      return;
    }

    try {
      this.callbacks.onMessage('Rejecting edits...');
      const result = await modelEditPipelineService.rejectEdits(this.pendingEditIds);
      
      if (result.success) {
        this.callbacks.onMessage(`✓ Rejected ${result.rejected_count} edits`);
        this.pendingEditIds = []; // Clear rejected edits
      } else {
        throw new Error('Failed to reject some edits');
      }
      
      this.callbacks.onEditsRejected(result);
    } catch (error: any) {
      const errorMessage = typeof error === 'string' ? error : 
                         error?.message || 'Failed to reject edits';
      this.callbacks.onError(errorMessage);
      throw error;
    }
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
      const extractRes = await modelEditPipelineService.extractMetadataChunks(filePath)
      .catch((error: any) => {
        throw new Error(this.getErrorMessage(error));
      });
      
      if (!extractRes.data.chunks?.length) {
        throw new Error('No data was extracted from the Excel file');
      }

      // Step 2: Compress chunks
      this.callbacks.onMessage('Processing extracted data...');
      const compressRes = await modelEditPipelineService.compressChunks(extractRes.data.chunks);
      
      if (!compressRes.data.compressed_texts?.length) {
        throw new Error('Failed to process the extracted data');
      }

      // Step 3: Store embeddings
      this.callbacks.onMessage('Storing data for editing...');
      const storeRes = await modelEditPipelineService.storeEmbeddings(
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
      this.callbacks.onMessage('✓ Data processing complete! You can now request edits to your file.');
      return true;

    } catch (error: any) {
      const errorMessage = typeof error === 'string' ? error : 
                        error?.message || 'An unknown error occurred';
      this.callbacks.onError(errorMessage);
      this.isDataReady = false;
      this.callbacks.onDataReady(false);
      return false;
    } finally {
      this.callbacks.onProcessingChange(false);
    }
  }


async processEditRequest(editRequest: string): Promise<void> {
    if (!this.isDataReady || !this.currentWorkbookPath) {
      this.callbacks.onError('Please process an Excel file first');
      return;
    }
  
    this.callbacks.onProcessingChange(true);
    this.callbacks.onTypingStart();
    this.callbacks.onMessage('Processing your edit request...');
  
    try {
      // Step 1: Search for relevant chunks
      this.callbacks.onMessage('Searching for relevant data...');
      const searchResponse = await modelEditPipelineService.searchEmbeddings(
        editRequest,         // query
        this.currentWorkbookPath, // workbookPath
        3                     // topK
      );

      if (!searchResponse.data.results?.length) {
        this.callbacks.onError('No relevant data found to process your edit');
        return;
      }

  
      // Step 2: Generate edit metadata with the found chunks
      this.callbacks.onMessage('Generating edit instructions...');
      const metadataStr = await modelEditPipelineService.generateEditMetadata({
        user_request: editRequest,
        chunks: searchResponse.data.results,
        chunk_limit: searchResponse.data.results.length
      });

      // Step 3: Parse the metadata
      const parsedMetadata = await modelEditPipelineService.parseMetadata(metadataStr);
      
      // Step 4: Apply the edits
      this.callbacks.onMessage('Applying changes to Excel file...');
      const result = await modelEditPipelineService.applyEdit(
        this.currentWorkbookPath,
        parsedMetadata
      );

      // Store pending edits
      this.storePendingEdits(result);

      // Notify completion
      this.callbacks.onMessage('✓ Changes applied successfully!');
      this.callbacks.onEditComplete(result);

    } catch (error: any) {
      const errorMessage = typeof error === 'string' ? error : 
                        error?.message || 'An unknown error occurred';
      this.callbacks.onError(errorMessage);
    } finally {
      this.callbacks.onTypingEnd();
      this.callbacks.onProcessingChange(false);
    }
  }

 
  private getErrorMessage(error: any): string {
    if (error?.response?.data?.detail) {
      // Handle validation errors (422)
      if (error.response.status === 422) {
        const detail = error.response.data.detail;
        if (Array.isArray(detail)) {
          // Format validation errors into a readable string
          return detail.map(err => `${err.loc.join('.')}: ${err.msg}`).join('\n');
        }
        return String(detail);
      }
      return String(error.response.data.detail);
    }
    return error?.message || 'An unknown error occurred';
  }

    /**
     * Clean up resources and reset service state
     */
    cleanup(): void {
        try {
        // Reset service state
        this.isDataReady = false;
        this.currentWorkbookPath = null;
        
        // Notify listeners that data is no longer ready
        this.callbacks.onDataReady(false);
        this.callbacks.onMessage('Service cleanup complete');
        
        } catch (error: any) {
        console.error('Error during cleanup:', error);
        this.callbacks.onError('Error during cleanup: ' + (error.message || 'Unknown error'));
        }
    }
}

