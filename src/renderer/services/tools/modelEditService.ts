// src/renderer/services/tools/modelEditService.ts
import modelEditPipelineService from '../python-api/modelEditPipelineService';
import qaPipelineService from '../python-api/qaPipelineService';

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
}

export class ModelEditService {
  private callbacks: ModelEditCallbacks;
  private isDataReady = false;
  private currentWorkbookPath: string | null = null;

  constructor(callbacks: ModelEditCallbacks) {
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

