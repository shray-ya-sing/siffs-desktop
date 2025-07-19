// src/renderer/services/python-api/modelEditPipelineService.ts
import axios, { 
  AxiosInstance, 
  AxiosRequestConfig, 
  AxiosResponse, 
  AxiosError,
  CancelTokenSource,
  AxiosRequestHeaders
} from 'axios';

const isDev = process.env.NODE_ENV === 'development';
const baseURL = isDev 
  ? 'http://127.0.0.1:3001/api'
  : 'http://127.0.0.1:5001/api';

// Create a custom axios instance with default config
const apiClient: AxiosInstance = axios.create({
  baseURL,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: false,
  timeout: 300000, // 5 minute timeout for long-running operations
});

// Request interceptor for API calls
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error: AxiosError) => {
    console.error('Request error:', error);
    return Promise.reject(error);
  }
);

// Response interceptor for handling errors
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response) {
      console.error('API Error:', {
        status: error.response.status,
        data: error.response.data,
        headers: error.response.headers,
      });
    } else if (error.request) {
      console.error('No response received:', error.request);
    } else {
      console.error('Error:', error.message);
    }
    return Promise.reject(error);
  }
);

interface GenerateEditMetadataParams {
    user_request: string;
    chunks?: any[];  // Add chunks parameter
    chunk_limit?: number;  // Add chunk limit
    model?: string;
    max_tokens?: number;
    temperature?: number;
    stream?: boolean;
}

interface ParseMetadataParams {
  metadata: string;
  strict?: boolean;
}

interface EditExcelParams {
  file_path: string;
  metadata: Record<string, any[]>;
  visible?: boolean;
}

interface PipelineResult {
  status: string;
  message: string;
  file_path: string;
  modified_sheets: string[];
}

interface SearchEmbeddingsParams {
  query: string;
  workbook_path: string;
  top_k?: number;
}

interface SearchResult {
  text: string;
  markdown: string;
  score: number;
  metadata: Record<string, any>;
}

interface SearchResponse {
  status: string;
  results: SearchResult[];
  total_chunks: number;
}

// Define response types
interface Chunk {
  text: string;
  markdown: string;
  metadata: Record<string, any>;
  [key: string]: any; // For additional properties
}

interface ExtractMetadataResponse {
  status: string;
  chunks: Chunk[];
  file_path: string;
}

interface CompressChunksResponse {
  status: string;
  compressed_texts: string[];
  compressed_markdown_texts: string[];
}

interface StoreEmbeddingsResponse {
  status: string;
  workbook_id: string;
  chunks_stored: number;
  embedding_model: string;
}

export interface AcceptEditsResponse {
  success: boolean;
  accepted_count: number;
  failed_ids: string[];
  accepted_edit_version_ids: number[];
}

export interface RejectEditsResponse {
  success: boolean;
  rejected_count: number;
  failed_ids: string[];
}

const modelEditPipelineService = {

    /**
   * Start a new Excel session
   */
  async startExcelSession(filePath: string, visible: boolean = false): Promise<{ status: string; message: string }> {
    const response = await apiClient.post('/excel/start-excel-session', {
      file_path: filePath,
      visible
    });
    return response.data;
  },

  /**
   * End an Excel session
   */
  async endExcelSession(filePath: string, save: boolean = true): Promise<{ status: string; message: string }> {
    const response = await apiClient.post('/excel/end-excel-session', {
      file_path: filePath,
      save
    });
    return response.data;
  },

  /**
   * Save an Excel session without closing it
   */
  async saveExcelSession(filePath: string): Promise<{ status: string; message: string }> {
    const response = await apiClient.post('/excel/save-excel-session', {
      file_path: filePath
    });
    return response.data;
  },

  /**
       * Extract metadata chunks from an Excel file
       * @param filePath Path to the Excel file
       * @param rowsPerChunk Number of rows per chunk (default: 10)
       * @param maxColsPerSheet Maximum columns per sheet (default: 50)
       * @param includeDependencies Whether to include cell dependencies (default: true)
       * @returns Promise with extracted chunks
       */
      extractMetadataChunks(
        filePath: string,
        rowsPerChunk: number = 10,
        maxColsPerSheet: number = 50,
        includeDependencies: boolean = true
      ): Promise<AxiosResponse<ExtractMetadataResponse>> {
        return apiClient.post<ExtractMetadataResponse>('/excel/extract-metadata-chunks', {
          filePath,
          rows_per_chunk: rowsPerChunk,
          max_cols_per_sheet: maxColsPerSheet,
          include_dependencies: includeDependencies,
          include_empty_chunks: false
        });
      },
    
      /**
       * Compress metadata chunks to text and markdown
       * @param chunks Array of chunks to compress
       * @param maxCellsPerChunk Maximum cells per chunk (default: 1000)
       * @param maxCellLength Maximum length of cell content (default: 200)
       * @returns Promise with compressed text and markdown
       */
      compressChunks(
        chunks: Chunk[],
        maxCellsPerChunk: number = 1000,
        maxCellLength: number = 200
      ): Promise<AxiosResponse<CompressChunksResponse>> {
        return apiClient.post<CompressChunksResponse>('/excel/compress-chunks', {
          chunks: chunks,
          max_cells_per_chunk: maxCellsPerChunk,
          max_cell_length: maxCellLength
        });
      },
    
      /**
       * Store embeddings for the given chunks
       * @param workbookPath Path to the workbook
       * @param chunks Array of chunks with text and markdown
       * @param modelName Name of the embedding model (default: 'msmarco-MiniLM-L-6-v3')
       * @param createNewVersion Whether to create a new version of the workbook (default: true)
       * @returns Promise with storage results
       */
      storeEmbeddings(
        workbookPath: string,
        chunks: Chunk[],
        modelName: string = 'msmarco-MiniLM-L-6-v3',
        createNewVersion: boolean = true
      ): Promise<AxiosResponse<StoreEmbeddingsResponse>> {
        return apiClient.post<StoreEmbeddingsResponse>('/vectors/storage/embed-and-store-chunks', {
          workbook_path: workbookPath,
          chunks: chunks,
          embedding_model: modelName,
          create_new_version: createNewVersion
        });
      },
    
      /**
       * Search stored embeddings
       * @param query Search query
       * @param workbookPath Path to the workbook (optional, searches all if not provided)
       * @param topK Number of results to return (default: 5)
       * @returns Promise with search results
       */
      searchEmbeddings(
        query: string,
        workbookPath?: string,
        topK: number = 5
      ): Promise<AxiosResponse<SearchResponse>> {
        const payload: Record<string, any> = {
          query,
          top_k: topK,
          return_format: 'both' // Get both text and markdown
        };
    
        if (workbookPath) {
          payload.workbook_path = workbookPath;
        }
    
        return apiClient.post<SearchResponse>('/vectors/search/query', payload);
      },

  /**
   * Generate edit metadata for Excel using LLM
   * @param params Parameters for edit metadata generation
   * @param chunks List of search result chunks with markdown and metadata
   * @param chunk_limit Maximum number of chunks to process (default: 10)
   * @returns Promise with the generated metadata string
   */
  async generateEditMetadata(params: GenerateEditMetadataParams): Promise<string> {
    const response = await apiClient.post('/excel/generate-edit-metadata', {
      
      user_request: params.user_request,
      chunks: params.chunks || [],
      chunk_limit: params.chunk_limit || 10,
      model: params.model || 'claude-3-5-sonnet-20241022',
      max_tokens: params.max_tokens || 2000,
      temperature: params.temperature || 0.3,
      stream: params.stream || false,
    });
    
    return params.stream ? response.data : response.data.result;
  },

  /**
   * Parse metadata string into structured format
   * @param metadataString The metadata string to parse
   * @param strict Whether to use strict parsing (default: true)
   * @returns Promise with parsed metadata
   */
  async parseMetadata(metadataString: string, strict: boolean = true): Promise<any> {
    const response = await apiClient.post('/excel/parse-metadata', {
      metadata: metadataString,
      strict
    });
    return response.data.data;
  },

  /**
   * Apply metadata changes to an Excel file
   * @param filePath Path to the Excel file
   * @param metadata Parsed metadata to apply
   * @param visible Whether to show Excel during editing (default: true)
   * @returns Promise with the edit result
   */
  async applyEdit(filePath: string, metadata: any, visible: boolean = true): Promise<PipelineResult> {
    const response = await apiClient.post('/excel/edit-excel', {
      file_path: filePath,
      metadata: metadata,
      visible
    });
    return response.data;
  },

  /**
   * Accept pending edits by their IDs
   * @param editIds Array of edit IDs to accept
   * @returns Promise with accept operation result
   */
  async acceptEdits(editIds: string[]): Promise<AcceptEditsResponse> {
    const response = await apiClient.post('/excel/edits/accept', {
      edit_ids: editIds
    });
    return response.data;
  },

    /**
   * Reject pending edits by their IDs
   * @param editIds Array of edit IDs to reject
   * @returns Promise with reject operation result
   */
  async rejectEdits(editIds: string[]): Promise<RejectEditsResponse> {
    const response = await apiClient.post('/excel/edits/reject', {
      edit_ids: editIds
    });
    return response.data;
  },


  /**
   * Stream edit metadata generation for real-time updates
   * @param userRequest User's edit instructions
   * @param onChunk Callback for each chunk of generated metadata
   * @param onError Callback for errors
   */
  async streamEditMetadataGeneration(
    userRequest: string,
    chunks: any[] = [],  // Add chunks parameter
    chunkLimit: number = 10,  // Add chunk limit
    onChunk: (chunk: string) => void,
    onError: (error: string) => void
  ) {
    try {
      const response = await apiClient.post(
        '/excel/generate-edit-metadata',
        {
          user_request: userRequest,
          chunks: chunks,
          chunk_limit: chunkLimit,
          stream: true,
        },
        {
          responseType: 'stream',
        }
      );
  
      // Handle streaming response
      const reader = response.data.getReader();
      const decoder = new TextDecoder();
      let buffer = '';  // Buffer to accumulate chunks
      
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        const chunk = decoder.decode(value, { stream: true });
        buffer += chunk;
        
        // Process complete SSE messages
        const lines = buffer.split('\n\n');
        buffer = lines.pop() || '';  // Keep incomplete message in buffer
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.replace('data: ', '');
            if (data.trim() === '[DONE]') {
              continue;
            }
            try {
              const parsed = JSON.parse(data);
              if (parsed.chunk) {
                onChunk(parsed.chunk);
              } else if (parsed.error) {
                throw new Error(parsed.error);
              }
            } catch (e) {
              console.error('Error parsing SSE data:', e);
            }
          }
        }
      }
    } catch (error: any) {
      console.error('Streaming error:', error);
      onError(error.message || 'Error during edit metadata generation');
    }
  }
};

export default modelEditPipelineService;