import apiService from './pythonApiService';

// Types
interface ChunkInfo {
  chunk_index: number;
  token_count: number;
  line_count: number;
  character_count: number;
  sheets: string[];
  table_rows: number;
  has_dependency_summary: boolean;
  has_header: boolean;
  token_efficiency: number;
}

interface ExtractionResult {
  chunks: string[];
  chunkInfo: ChunkInfo[];
  metadata: any;
  markdown: string;
}

interface ModelAuditCallbacks {
  onSystemEvent: (message: string, type: 'info' | 'extracting' | 'completed' | 'reviewing' | 'error') => void;
  onAnalysisChunk: (chunk: string, isDone: boolean) => void;
  onAnalysisError: (error: string) => void;
  onProgressUpdate: (current: number, total: number) => void;
}

interface ModelAuditState {
  isProcessing: boolean;
  isStreaming: boolean;
  streamingComplete: boolean;
  analysisResult: string;
}

export class ModelAuditService {
  private cancelRef: (() => void) | null = null;
  private callbacks: ModelAuditCallbacks;
  private state: ModelAuditState;

  constructor(callbacks: ModelAuditCallbacks) {
    this.callbacks = callbacks;
    this.state = {
      isProcessing: false,
      isStreaming: false,
      streamingComplete: false,
      analysisResult: ''
    };
  }

  // Getters for state
  get isProcessing() { return this.state.isProcessing; }
  get isStreaming() { return this.state.isStreaming; }
  get streamingComplete() { return this.state.streamingComplete; }
  get analysisResult() { return this.state.analysisResult; }

  // State setters with callback notifications
  private setState(updates: Partial<ModelAuditState>) {
    this.state = { ...this.state, ...updates };
  }

  // Validate file path
  private validateFilePath(path: string): boolean {
    return path.trim().toLowerCase().endsWith('.xlsx');
  }

  // Handle extraction phase
  private async handleExtraction(filePath: string): Promise<ExtractionResult | null> {
    try {
      this.callbacks.onSystemEvent('Getting the data from your file...', 'extracting');
      
      const metadataResponse = await apiService.extractExcelMetadata(filePath);
      
      // Validate response
      if (metadataResponse.data.status !== 'success') {
        this.callbacks.onSystemEvent('Failed to extract data from your file', 'error');
        return null;
      }

      // Check that chunks were created
      if (!metadataResponse.data.chunks || metadataResponse.data.chunks.length === 0) {
        this.callbacks.onSystemEvent('No data chunks created from your file', 'error');
        return null;
      }

      // Check that chunks contain data
      const nonEmptyChunks = metadataResponse.data.chunks.filter(chunk => chunk.trim().length > 0);
      if (nonEmptyChunks.length === 0) {
        this.callbacks.onSystemEvent('Failed to extract meaningful data from your file', 'error');
        return null;
      }

      // Calculate statistics for user feedback
      const totalTokens = metadataResponse.data.chunk_info?.reduce((sum, info) => sum + info.token_count, 0) || 0;
      const sheetsFound = new Set(
        metadataResponse.data.chunk_info?.flatMap(info => info.sheets) || []
      ).size;

      this.callbacks.onSystemEvent(
        `Data extracted successfully - ${metadataResponse.data.chunks.length} chunks created (${totalTokens.toLocaleString()} tokens, ${sheetsFound} sheets)`, 
        'completed'
      );

      return {
        chunks: metadataResponse.data.chunks,
        chunkInfo: metadataResponse.data.chunk_info || [],
        metadata: metadataResponse.data.metadata,
        markdown: metadataResponse.data.markdown || ''
      };

    } catch (error) {
      console.error('Extraction error:', error);
      this.callbacks.onSystemEvent('Failed to extract data from your file', 'error');
      return null;
    }
  }

  // Handle analysis phase
  private async handleAnalysis(chunksToAnalyze: string[], chunkInfoToUse: ChunkInfo[]): Promise<void> {
    if (chunksToAnalyze.length === 0) {
      this.callbacks.onSystemEvent('No chunks available for analysis', 'error');
      this.setState({
        isStreaming: false,
        streamingComplete: true,
        isProcessing: false
      });
      return;
    }

    try {
      this.setState({
        isStreaming: true,
        streamingComplete: false,
        analysisResult: ''
      });

      // Show analysis progress
      const totalTokens = chunkInfoToUse.reduce((sum, info) => sum + info.token_count, 0);
      this.callbacks.onSystemEvent(
        `Analyzing your file (${chunksToAnalyze.length} chunks, ${totalTokens.toLocaleString()} tokens)...`, 
        'reviewing'
      );

      // Track analysis progress
      let fullAnalysis = '';
      let chunksProcessed = 0;
      
      // Call the analyze chunks API
      const { cancel } = apiService.analyzeExcelChunks(
        chunksToAnalyze,
        (chunk, isDone) => {
          if (isDone) {
            this.setState({
              streamingComplete: true,
              isStreaming: false,
              isProcessing: false
            });
            
            // Add completion event after a small delay
            setTimeout(() => {
              this.callbacks.onSystemEvent('Analysis completed successfully', 'completed');
            }, 500);
            return;
          }
          
          // Handle chunk content
          if (chunk) {
            // Check if this is a chunk separator/header
            if (chunk.includes('--- ANALYZING CHUNK') || chunk.includes('--- END OF CHUNK')) {
              // Track progress
              if (chunk.includes('--- ANALYZING CHUNK')) {
                chunksProcessed++;
                const progress = Math.round((chunksProcessed / chunksToAnalyze.length) * 100);
                console.log(`Processing chunk ${chunksProcessed}/${chunksToAnalyze.length} (${progress}%)`);
                this.callbacks.onProgressUpdate(chunksProcessed, chunksToAnalyze.length);
              }
            }
            
            // Append chunk to analysis result
            fullAnalysis += chunk;
            this.setState({
              analysisResult: this.state.analysisResult + chunk
            });
            
            // Call the chunk callback
            this.callbacks.onAnalysisChunk(chunk, false);
          }
        },
        (error) => {
          console.error('Analysis error:', error);
          this.callbacks.onSystemEvent(`Analysis error: ${error}`, 'error');
          this.callbacks.onAnalysisError(error);
          this.setState({
            isStreaming: false,
            streamingComplete: true,
            isProcessing: false
          });
        }
      );

      // Store the cancel function
      this.cancelRef = cancel;

    } catch (error) {
      console.error('Error during analysis:', error);
      this.callbacks.onSystemEvent('Failed to analyze file', 'error');
      this.setState({
        isStreaming: false,
        streamingComplete: true,
        isProcessing: false
      });
    }
  }

  // Main public method to start the audit process
  async startAudit(filePath: string): Promise<ExtractionResult | null> {
    if (!filePath.trim() || this.state.isProcessing) {
      return null;
    }

    // Validate file path
    if (!this.validateFilePath(filePath)) {
      throw new Error('File path must end with .xlsx. Don\'t include quotes around the file name.');
    }

    // Clear previous results
    this.setState({
      isProcessing: true,
      isStreaming: false,
      streamingComplete: false,
      analysisResult: ''
    });
    
    // Add initial system event
    this.callbacks.onSystemEvent('Starting model audit...', 'info');

    try {
      // Phase 1: Extract data and create chunks
      const extractionResult = await this.handleExtraction(filePath);
      
      if (!extractionResult) {
        this.setState({ isProcessing: false });
        return null;
      }

      // Small delay to let the user see the extraction completion
      await new Promise(resolve => setTimeout(resolve, 500));

      // Phase 2: Analyze the chunks - pass the extracted data directly
      await this.handleAnalysis(extractionResult.chunks, extractionResult.chunkInfo);

      return extractionResult;

    } catch (error) {
      console.error('Error in startAudit:', error);
      this.callbacks.onSystemEvent('Unexpected error during processing', 'error');
      this.setState({
        isProcessing: false,
        isStreaming: false,
        streamingComplete: true
      });
      throw error;
    }
  }

  // Cancel current operation
  cancel(): void {
    if (this.cancelRef) {
      this.cancelRef();
      this.cancelRef = null;
    }
    this.setState({
      isProcessing: false,
      isStreaming: false
    });
    this.callbacks.onSystemEvent('Operation cancelled by user', 'info');
  }

  // Reset state
  reset(): void {
    this.setState({
      isProcessing: false,
      isStreaming: false,
      streamingComplete: false,
      analysisResult: ''
    });
    if (this.cancelRef) {
      this.cancelRef();
      this.cancelRef = null;
    }
  }
}

export type { ChunkInfo, ExtractionResult, ModelAuditCallbacks, ModelAuditState };