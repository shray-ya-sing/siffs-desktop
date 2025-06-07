// src/renderer/services/tools/modelCreateService.ts
import modelCreatePipelineService from '../python-api/modelCreatePipelineService';

export interface ModelCreateCallbacks {
  onMessage: (message: string) => void;
  onError: (error: string) => void;
  onProcessingChange: (isProcessing: boolean) => void;
  onProgress: (step: string, message: string) => void;
  onComplete: (result: any) => void;
}

export class ModelCreateService {
  private callbacks: ModelCreateCallbacks;
  private currentFilePath: string | null = null;

  constructor(callbacks: ModelCreateCallbacks) {
    this.callbacks = callbacks;
  }

  /**
   * Process the Excel file creation with the given instructions
   * @param filePath Path to the Excel file
   * @param instructions User's instructions for model creation
   */
  async processExcelFile(filePath: string, instructions: string): Promise<void> {
    if (!filePath) {
      this.callbacks.onError('File path is required');
      return;
    }

    this.currentFilePath = filePath;
    this.callbacks.onProcessingChange(true);
    this.callbacks.onMessage('Starting model creation process...');

    try {
      await modelCreatePipelineService.executePipeline(
        filePath,
        instructions,
        {
          onProgress: (step, message) => {
            this.callbacks.onProgress(step, message);
            this.callbacks.onMessage(message);
          },
          onError: (error) => {
            this.callbacks.onError(error);
            this.callbacks.onProcessingChange(false);
          },
          onComplete: (result) => {
            this.callbacks.onMessage('✓ Model creation completed successfully!');
            this.callbacks.onComplete(result);
            this.callbacks.onProcessingChange(false);
          },
        }
      );
    } catch (error: any) {
      this.callbacks.onError(error.message || 'Failed to process Excel file');
      this.callbacks.onProcessingChange(false);
    }
  }

  /**
   * Clean up resources when the service is no longer needed
   */
  cleanup(): void {
    this.currentFilePath = null;
  }
}