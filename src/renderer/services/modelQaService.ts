// src/renderer/services/modelQaService.ts
import apiService from './pythonApiService';
import { Message } from '../types/message';

export interface ModelQACallbacks {
  // Called when a new message is received from the assistant
  onMessage: (message: string) => void;
  // Called when an error occurs during processing
  onError: (error: string) => void;
  // Called when processing starts/stops
  onProcessingChange: (isProcessing: boolean) => void;
  onTypingStart: () => void;
  onTypingEnd: () => void;
}

export class ModelQAService {
  private callbacks: ModelQACallbacks;
  private cancelRef: (() => void) | null = null;
  private isProcessing = false;

  constructor(callbacks: ModelQACallbacks) {
    this.callbacks = callbacks;
  }

  /**
   * Process a user message and get a response from the QA service
   * @param filePath Path to the Excel file being analyzed
   * @param userMessage The user's message/query
   * @returns A promise that resolves when the response is complete
   */
  public async processMessage(filePath: string, userMessage: string): Promise<void> {
    if (!filePath || !userMessage.trim()) {
      this.callbacks.onError('File path and message are required');
      return;
    }

    try {
      this.setProcessing(true);

      // Call the API to get the response
      const { cancel } = apiService.queryExcel(
        filePath,
        userMessage,
        (chunk, isDone) => {
          if (chunk) {
            this.callbacks.onMessage(chunk);
          }
          
          if (isDone) {
            this.setProcessing(false);
          }
        },
        (error) => {
          this.handleError(error);
        }
      );

      // Store the cancel function
      this.cancelRef = cancel;

    } catch (error) {
      this.handleError(error);
    }
  }

  /**
   * Cancel the current operation
   */
  public cancel(): void {
    if (this.cancelRef) {
      this.cancelRef();
      this.cancelRef = null;
    }
    this.setProcessing(false);
  }

  /**
   * Clean up resources
   */
  public cleanup(): void {
    this.cancel();
  }

  // Helper methods
  private setProcessing(isProcessing: boolean): void {
    this.isProcessing = isProcessing;
    this.callbacks.onProcessingChange(isProcessing);
  }

  private handleError(error: any): void {
    console.error('ModelQA Error:', error);
    const errorMessage = error?.message || 'An unknown error occurred';
    this.callbacks.onError(errorMessage);
    this.setProcessing(false);
  }
}

export default ModelQAService;