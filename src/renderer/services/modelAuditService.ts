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

  // State setters
  private setState(updates: Partial<ModelAuditState>) {
    this.state = { ...this.state, ...updates };
  }

  // Validate file path
  private validateFilePath(path: string): boolean {
    return path.trim().toLowerCase().endsWith('.xlsx');
  }

  // Step 1: Extract raw metadata from Excel file
  private async extractMetadata(filePath: string): Promise<{ metadata: any; displayValues: any } | null> {
    try {
      this.callbacks.onSystemEvent('Step 1: Extracting data from Excel file...', 'extracting');
      
      const extractResponse = await apiService.extractExcelMetadataRaw(filePath);
      
      if (extractResponse.data.status !== 'success') {
        this.callbacks.onSystemEvent('Failed to extract data from Excel file', 'error');
        return null;
      }

      const { metadata, display_values } = extractResponse.data;
      
      // Calculate basic statistics for user feedback
      const sheetsCount = metadata?.sheets?.length || 0;
      const totalCells = metadata?.sheets?.reduce((total: number, sheet: any) => {
        return total + (sheet.cellData?.flat().length || 0);
      }, 0) || 0;

      this.callbacks.onSystemEvent(
        `✓ Metadata extracted successfully - ${sheetsCount} sheets, ${totalCells.toLocaleString()} cells processed`, 
        'completed'
      );

      return { metadata, displayValues: display_values };

    } catch (error) {
      console.error('Metadata extraction error:', error);
      this.callbacks.onSystemEvent('Failed to extract data from Excel file', 'error');
      return null;
    }
  }

  // Step 2: Compress metadata to markdown
  private async compressToMarkdown(metadata: any, displayValues: any): Promise<string | null> {
    try {
      this.callbacks.onSystemEvent('Step 2: Getting the rest of the data...', 'extracting');
      
      const compressResponse = await apiService.compressMetadataToMarkdown(metadata, displayValues);
      
      if (compressResponse.data.status !== 'success') {
        this.callbacks.onSystemEvent('Failed to get the rest of the data', 'error');
        return null;
      }

      const { markdown } = compressResponse.data;
      
      // Calculate markdown statistics
      const lineCount = markdown.split('\n').length;
      const charCount = markdown.length;
      const sizeKB = Math.round(charCount / 1024);

      this.callbacks.onSystemEvent(
        `✓ Markdown generated successfully - ${lineCount.toLocaleString()} lines, ${sizeKB}KB`, 
        'completed'
      );

      return markdown;

    } catch (error) {
      console.error('Markdown compression error:', error);
      this.callbacks.onSystemEvent('Failed to get the rest of the data', 'error');
      return null;
    }
  }

  // Step 3: Chunk markdown content
  private async chunkMarkdown(markdown: string): Promise<{ chunks: string[]; chunkInfo: ChunkInfo[] } | null> {
    try {
      this.callbacks.onSystemEvent('Step 3: Organizing data for analysis...', 'extracting');
      
      const chunkResponse = await apiService.chunkMarkdownContent(markdown);
      
      if (chunkResponse.data.status !== 'success') {
        this.callbacks.onSystemEvent('Failed to organize data for analysis', 'error');
        return null;
      }

      const { chunks, chunk_info } = chunkResponse.data;

      // Validate chunks
      if (!chunks || chunks.length === 0) {
        this.callbacks.onSystemEvent('Data wasn\'t organized correctly, failed to process', 'error');
        return null;
      }

      // Check that chunks contain meaningful data
      const nonEmptyChunks = chunks.filter(chunk => chunk.trim().length > 0);
      if (nonEmptyChunks.length === 0) {
        this.callbacks.onSystemEvent('Failed to organize data for analysis', 'error');
        return null;
      }

      // Calculate chunk statistics
      const totalTokens = chunk_info?.reduce((sum, info) => sum + info.token_count, 0) || 0;
      const avgTokensPerChunk = Math.round(totalTokens / chunks.length);
      const sheetsFound = new Set(
        chunk_info?.flatMap(info => info.sheets) || []
      ).size;

      this.callbacks.onSystemEvent(
        `✓ Chunking completed - ${chunks.length} chunks created (${totalTokens.toLocaleString()} tokens, avg ${avgTokensPerChunk} per chunk, ${sheetsFound} sheets)`, 
        'completed'
      );

      return { chunks, chunkInfo: chunk_info || [] };

    } catch (error) {
      console.error('Markdown chunking error:', error);
      this.callbacks.onSystemEvent('Failed to organize data for analysis', 'error');
      return null;
    }
  }

  // Handle the complete extraction process using 3 steps
  private async handleExtraction(filePath: string): Promise<ExtractionResult | null> {
    try {
      this.callbacks.onSystemEvent('Starting data extraction process...', 'info');

      // Step 1: Extract metadata
      const extractResult = await this.extractMetadata(filePath);
      if (!extractResult) {
        return null;
      }

      // Small delay for UI feedback
      await new Promise(resolve => setTimeout(resolve, 300));

      // Step 2: Compress to markdown
      const markdown = await this.compressToMarkdown(extractResult.metadata, extractResult.displayValues);
      if (!markdown) {
        return null;
      }

      // Small delay for UI feedback
      await new Promise(resolve => setTimeout(resolve, 300));

      // Step 3: Chunk markdown
      const chunkResult = await this.chunkMarkdown(markdown);
      if (!chunkResult) {
        return null;
      }

      // Final success message
      this.callbacks.onSystemEvent(
        `🎉 Data extraction completed successfully! Ready for analysis.`, 
        'completed'
      );

      return {
        chunks: chunkResult.chunks,
        chunkInfo: chunkResult.chunkInfo,
        metadata: extractResult.metadata,
        markdown
      };

    } catch (error) {
      console.error('Extraction process error:', error);
      this.callbacks.onSystemEvent('Data extraction process failed', 'error');
      return null;
    }
  }

  // Handle analysis phase
  private async handleAnalysis(chunksToAnalyze: string[], chunkInfoToUse: ChunkInfo[]): Promise<void> {
    if (chunksToAnalyze.length === 0) {
      this.callbacks.onSystemEvent('No data available for analysis', 'error');
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

            if (chunk.includes('Analysis complete.')) {
              this.setState({
                streamingComplete: true,
                isStreaming: false,
                isProcessing: false
              });
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
      // Phase 1: Extract data using 3-step process
      const extractionResult = await this.handleExtraction(filePath);
      
      if (!extractionResult) {
        this.setState({ isProcessing: false });
        return null;
      }

      // Small delay to let the user see the extraction completion
      await new Promise(resolve => setTimeout(resolve, 800));

      // Phase 2: Analyze the chunks
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