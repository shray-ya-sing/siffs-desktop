import axios, { 
  AxiosInstance, 
  AxiosRequestConfig, 
  AxiosResponse, 
  AxiosError,
  InternalAxiosRequestConfig,
  AxiosRequestHeaders
} from 'axios';


// Define response types
interface HealthCheckResponse {
  status: string;
  message: string;
}

interface ExampleResponse {
  message: string;
}

interface ExcelMetadataResponse {
  status: string;
  markdown: string;
  metadata: any;
  chunks: string[];
  chunk_info: Array<{
    chunk_index: number;
    token_count: number;
    line_count: number;
    character_count: number;
    sheets: string[];
    table_rows: number;
    has_dependency_summary: boolean;
    has_header: boolean;
    token_efficiency: number;
  }>;
  temp_file?: string;
}

interface ExtractMetadataResponse {
  status: string;
  metadata: any;
  display_values: any;
}

interface CompressMetadataResponse {
  status: string;
  markdown: string;
}

interface ChunkMetadataResponse {
  status: string;
  chunks: string[];
  chunk_info: Array<{
    chunk_index: number;
    token_count: number;
    line_count: number;
    character_count: number;
    sheets: string[];
    table_rows: number;
    has_dependency_summary: boolean;
    has_header: boolean;
    token_efficiency: number;
  }>;
}

interface StreamChunk {
  chunk?: string;
  error?: string;
}

const isDev = process.env.NODE_ENV === 'development';

const baseURL = isDev 
    ? 'http://127.0.0.1:3001/api'
    : 'http://127.0.0.1:5001/api';


// Create a custom axios instance with default config
const apiClient: AxiosInstance = axios.create({
  baseURL,
  headers: {
    'Content-Type': 'application/json',
  } as AxiosRequestHeaders,
  withCredentials: false,
});

// Request interceptor for API calls
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig): InternalAxiosRequestConfig => {
    const token = localStorage.getItem('token');
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error: AxiosError): Promise<never> => {
    return Promise.reject(error);
  }
);

// Response interceptor for handling errors
apiClient.interceptors.response.use(
  (response: AxiosResponse) => response,
  (error: AxiosError) => {
    if (error.response) {
      console.error('API Error:', error.response.data);
      console.error('Status:', error.response.status);
      console.error('Headers:', error.response.headers);
    } else if (error.request) {
      console.error('No response received:', error.request);
    } else {
      console.error('Error:', error.message);
    }
    return Promise.reject(error);
  }
);

// API service methods
const apiService = {
  // Health check
  healthCheck(): Promise<AxiosResponse<HealthCheckResponse>> {
    return apiClient.get<HealthCheckResponse>('/health');
  },

  // Example endpoint
  getExample(): Promise<AxiosResponse<ExampleResponse>> {
    return apiClient.get<ExampleResponse>('/example');
  },

  /**
   * Step 1: Extract raw metadata from Excel file
   * @param filePath The path to the Excel file
   * @param maxRowsPerSheet Maximum rows per sheet to process (default: 100)
   * @param maxColsPerSheet Maximum columns per sheet to process (default: 50)
   * @param includeDisplayValues Whether to include display values (default: false)
   * @returns Promise with extracted metadata and display values
   */
  extractExcelMetadataRaw(
    filePath: string,
    maxRowsPerSheet: number = 100,
    maxColsPerSheet: number = 50,
    includeDisplayValues: boolean = false
  ): Promise<AxiosResponse<ExtractMetadataResponse>> {
    return apiClient.post<ExtractMetadataResponse>('/excel/extract-metadata', {
      filePath,
      max_rows_per_sheet: maxRowsPerSheet,
      max_cols_per_sheet: maxColsPerSheet,
      include_display_values: includeDisplayValues
    });
  },

  /**
   * Step 2: Compress metadata to markdown format
   * @param metadata The extracted metadata object
   * @param displayValues The display values object (optional)
   * @returns Promise with compressed markdown string
   */
  compressMetadataToMarkdown(
    metadata: any,
    displayValues: any = {}
  ): Promise<AxiosResponse<CompressMetadataResponse>> {
    return apiClient.post<CompressMetadataResponse>('/excel/compress-metadata', {
      metadata,
      display_values: displayValues
    });
  },

  /**
   * Step 3: Chunk markdown content into LLM-ready pieces
   * @param markdown The markdown string to chunk
   * @param maxTokens Maximum tokens per chunk (default: 18000)
   * @returns Promise with chunks array and chunk info
   */
  chunkMarkdownContent(
    markdown: string,
    maxTokens: number = 18000
  ): Promise<AxiosResponse<ChunkMetadataResponse>> {
    return apiClient.post<ChunkMetadataResponse>('/excel/chunk-metadata', {
      markdown,
      max_tokens: maxTokens
    });
  },

  /**
   * Extracts metadata from an Excel file and returns chunks.
   * @param filePath The path to the Excel file.
   * @returns A promise that resolves to the extracted metadata and chunks.
   * @deprecated Use extractExcelMetadataRaw, compressMetadataToMarkdown, and chunkMarkdownContent instead.
   */
  extractExcelMetadata(filePath: string): Promise<AxiosResponse<ExcelMetadataResponse>> {
    return apiClient.post<ExcelMetadataResponse>('/excel/extract-metadata', {
      filePath
    });
  },

  /**
   * Analyzes chunks from an Excel file using LLM with rate limiting and conversation memory.
   * @param chunks Array of markdown chunks to analyze.
   * @param onChunk A callback function to receive chunks of the analysis result.
   * @param onError A callback function to receive error messages.
   * @param model The LLM model to use (default: 'claude-3-5-sonnet-20241022').
   * @param temperature The sampling temperature (default: 0.3).
   * @returns An object with a cancel function to abort the analysis.
   */
  analyzeExcelChunks(
    chunks: string[],
    onChunk: (chunk: string, isDone: boolean) => void,
    onError: (error: string) => void,
    model: string = 'claude-3-5-sonnet-20241022', // claude-3-5-sonnet-20241022 or claude-3-5-haiku-20241022
    temperature: number = 0.3
  ): { cancel: () => void } {
    const controller = new AbortController();
    const signal = controller.signal;
    
    console.log(`Starting analysis of ${chunks.length} chunks with rate limiting and conversation memory`);
    
    // Start the fetch request
    fetch(`${baseURL}/excel/analyze-chunks`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        chunks,
        model,
        temperature
      }),
      signal
    })
    .then(async response => {
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      // Verify content type
      const contentType = response.headers.get('content-type');
      if (!contentType?.includes('text/event-stream') && !contentType?.includes('text/plain')) {
        console.warn('Unexpected content type:', contentType);
      }

      // Handle the stream
      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('No reader available');
      }

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        
        if (done) {
          console.log('Stream completed');
          onChunk('', true); // Signal completion
          break;
        }

        // Decode the chunk and process it
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || ''; // Keep the last incomplete line in the buffer

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6).trim();
            
            // Check for completion signal
            if (data === '[DONE]') {
              console.log('Received completion signal');
              onChunk('', true);
              return;
            }

            try {
              const parsed = JSON.parse(data);
              
              // Handle different message types
              if (parsed.error) {
                console.error('Server error:', parsed.error);
                onError(parsed.error);
                return;
              } 
              else if (parsed.chunk !== undefined) {
                // Regular content chunks - pass to user
                onChunk(parsed.chunk, false);
              }
              else if (parsed.info !== undefined) {
                // Info messages - log only
                console.log('📊 Info:', parsed.info);
              }
              else if (parsed.rate_limit !== undefined) {
                // Rate limit notifications - log only
                console.log('⏳ Rate limit:', parsed.rate_limit);
              }
              else if (parsed.wait_update !== undefined) {
                // Wait time updates - log only
                console.log('⏱️ Wait update:', parsed.wait_update);
              }
              else if (parsed.complete !== undefined) {
                // Completion message - log only
                console.log('✅ Analysis complete:', parsed.complete);
              }
              else {
                // Log any other message types for debugging
                console.log('🔍 Unknown message type:', parsed);
              }
              
            } catch (e) {
              console.error('Error parsing chunk:', e, 'Data:', data);
              // Don't call onError for parsing errors of individual chunks
              // as they might be partial data
            }
          }
          // Handle non-SSE format (direct JSON) - fallback
          else if (line.trim().startsWith('{')) {
            try {
              const parsed: StreamChunk = JSON.parse(line);
              if (parsed.error) {
                console.error('Server error in JSON line:', parsed.error);
                onError(parsed.error);
                return;
              } else if (parsed.chunk !== undefined) {
                onChunk(parsed.chunk, false);
              }
            } catch (e) {
              console.error('Error parsing JSON line:', e, 'Raw line:', line);
            }
          }
        }
      }
    })
    .catch(error => {
      if (error.name !== 'AbortError') {
        console.error('Error in analyzeExcelChunks:', error);
        onError(error.message || 'Failed to analyze chunks');
      } else {
        console.log('Analysis cancelled by user');
      }
    });

    // Return a cancel function
    return {
      cancel: () => {
        console.log('Cancelling chunk analysis');
        controller.abort();
      }
    };
  },

  /**
   * Legacy method - analyzes metadata from an Excel file using LLM.
   * @param metadata The metadata to analyze.
   * @param onChunk A callback function to receive chunks of the analysis result.
   * @param onError A callback function to receive error messages.
   * @param model The LLM model to use (default: 'claude-3-5-sonnet-20241022').
   * @param temperature The sampling temperature (default: 0.3).
   * @returns An object with a cancel function to abort the analysis.
   * @deprecated Use analyzeExcelChunks instead for better performance
   */
  analyzeExcelMetadata(
    metadata: any,  // or a more specific type if available
    onChunk: (chunk: string, isDone: boolean) => void,
    onError: (error: string) => void,
    model: string = 'claude-3-5-sonnet-20241022',
    temperature: number = 0.3
  ): { cancel: () => void } {
    const controller = new AbortController();
    const signal = controller.signal;
    
    // Start the fetch request
    fetch(`${baseURL}/excel/analyze-metadata`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        metadata,
        model,
        temperature
      }),
      signal
    })
    .then(async response => {
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      // Verify content type
      const contentType = response.headers.get('content-type');
      if (!contentType?.includes('text/event-stream') && !contentType?.includes('text/plain')) {
        console.warn('Unexpected content type:', contentType);
      }
  
      // Handle the stream
      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('No reader available');
      }
  
      const decoder = new TextDecoder();
      let buffer = '';
  
      while (true) {
        const { done, value } = await reader.read();
        
        if (done) {
          onChunk('', true); // Signal completion
          break;
        }
  
        // Decode the chunk and process it
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || ''; // Keep the last incomplete line in the buffer
  
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6).trim();
            
            // Check for completion signal
            if (data === '[DONE]') {
              onChunk('', true);
              return;
            }
  
            try {
              const parsed: StreamChunk = JSON.parse(data);
              if (parsed.error) {
                onError(parsed.error);
                return;
              } else if (parsed.chunk) {
                onChunk(parsed.chunk, false);
              }
            } catch (e) {
              console.error('Error parsing chunk:', e);
              onError('Error parsing server response');
              return;
            }
          }
          // Handle non-SSE format (direct JSON)
          else if (line.startsWith('{')) {
            try {
              const parsed: StreamChunk = JSON.parse(line);
              if (parsed.error) {
                onError(parsed.error);
                return false;
              } else if (parsed.chunk !== undefined) {
                onChunk(parsed.chunk, false);
              }
            } catch (e) {
              console.error('Error parsing JSON line:', e, 'Raw line:', line);
            }
          }
        }
      }
    })
    .catch(error => {
      if (error.name !== 'AbortError') {
        console.error('Error in analyzeExcelMetadata:', error);
        onError(error.message || 'Failed to analyze metadata');
      }
    });
  
    // Return a cancel function
    return {
      cancel: () => {
        controller.abort();
      }
    };
  },

  // Generic GET request
  get<T = any, R = AxiosResponse<T>>(
    url: string, 
    config?: AxiosRequestConfig
  ): Promise<R> {
    return apiClient.get<T, R>(url, config);
  },

  // Generic POST request
  post<T = any, R = AxiosResponse<T>>(
    url: string, 
    data?: T,
    config?: AxiosRequestConfig
  ): Promise<R> {
    return apiClient.post<T, R>(url, data, config);
  },

  // Generic PUT request
  put<T = any, R = AxiosResponse<T>>(
    url: string, 
    data?: T,
    config?: AxiosRequestConfig
  ): Promise<R> {
    return apiClient.put<T, R>(url, data, config);
  },

  // Generic DELETE request
  delete<T = any, R = AxiosResponse<T>>(
    url: string, 
    config?: AxiosRequestConfig
  ): Promise<R> {
    return apiClient.delete<T, R>(url, config);
  },

  /**
 * Mock API call with configurable delay
 * @param success Whether the mock call should succeed or fail
 * @param delayMs Delay in milliseconds (default: 10000ms)
 * @param mockData Optional mock data to return on success
 */
  mockApiCall<T = any>(
    success: boolean = true,
    delayMs: number = 10000,
    mockData?: T
  ): Promise<{ data: T; status: number }> {
    return new Promise((resolve, reject) => {
      setTimeout(() => {
        if (success) {
          resolve({
            data: mockData || { message: 'Mock API call successful' } as any,
            status: 200
          });
        } else {
          reject({
            response: {
              data: { error: 'Mock API call failed' },
              status: 500
            }
          });
        }
      }, delayMs);
    });
  }
};

export default apiService;