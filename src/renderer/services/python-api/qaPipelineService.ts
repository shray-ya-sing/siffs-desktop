import axios, { 
    AxiosInstance, 
    AxiosRequestConfig, 
    AxiosResponse, 
    AxiosError,
    CancelTokenSource,
    AxiosRequestHeaders
  } from 'axios';
  
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
  
  interface SearchResult {
    text: string;
    markdown: string;
    score: number;
    metadata: Record<string, any>;
    [key: string]: any; // For additional properties
  }
  
  interface SearchResponse {
    status: string;
    query: string;
    results: SearchResult[];
    total_chunks: number;
  }
  
  interface QAResponse {
    status: string;
    answer: string;
    sources?: string[];
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
    (response: AxiosResponse) => response,
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
  
  // API service methods
  const qaPipelineService = {
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
        chunks,
        max_cells_per_chunk: maxCellsPerChunk,
        max_cell_length: maxCellLength
      });
    },
  
    /**
     * Store embeddings for the given chunks
     * @param workbookPath Path to the workbook
     * @param chunks Array of chunks with text and markdown
     * @param modelName Name of the embedding model (default: 'msmarco-MiniLM-L-6-v3')
     * @param replaceExisting Whether to replace existing embeddings (default: true)
     * @returns Promise with storage results
     */
    storeEmbeddings(
      workbookPath: string,
      chunks: Chunk[],
      modelName: string = 'msmarco-MiniLM-L-6-v3',
      replaceExisting: boolean = true
    ): Promise<AxiosResponse<StoreEmbeddingsResponse>> {
      return apiClient.post<StoreEmbeddingsResponse>('/vectors/storage/embed-and-store-chunks', {
        workbook_path: workbookPath,
        chunks,
        embedding_model: modelName,
        replace_existing: replaceExisting
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
     * Ask a question based on search results
     * @param searchResponse Search results from searchEmbeddings
     * @param question The question to ask
     * @param model Model to use for QA (default: 'claude-sonnet-4-20250514')
     * @param includeSources Whether to include sources in the response (default: true)
     * @param cancelToken Optional cancel token for the request
     * @returns Promise with the answer
     */
    askQuestion(
      searchResponse: SearchResponse,
      question: string,
      model: string = 'claude-sonnet-4-20250514',
      includeSources: boolean = true,
      cancelToken?: CancelTokenSource
    ): Promise<AxiosResponse<QAResponse>> {
      const config: AxiosRequestConfig = {};
      
      if (cancelToken) {
        config.cancelToken = cancelToken.token;
      }
  
      return apiClient.post<QAResponse>('/excel/qa/from-search', {
        search_response: searchResponse,
        question,
        model,
        include_chunk_sources: includeSources
      }, config);
    },
  
    /**
     * Stream the answer to a question based on search results
     * @param searchResponse Search results from searchEmbeddings
     * @param question The question to ask
     * @param onChunk Callback for receiving chunks of the answer
     * @param onError Callback for errors
     * @param model Model to use for QA (default: 'claude-sonnet-4-20250514')
     * @param includeSources Whether to include sources in the response (default: true)
     * @returns Object with cancel function to abort the request
     */
    streamAnswer(
      searchResponse: SearchResponse,
      question: string,
      onChunk: (chunk: string, isDone: boolean) => void,
      onError: (error: string) => void,
      model: string = 'claude-sonnet-4-20250514',
      includeSources: boolean = true
    ): { cancel: () => void } {
      const controller = new AbortController();
      const signal = controller.signal;
  
      fetch(`${baseURL}/excel/qa/from-search`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          search_response: searchResponse,
          question,
          model,
          include_chunk_sources: includeSources
        }),
        signal
      })
      .then(async response => {
        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
        }
  
        const reader = response.body?.getReader();
        if (!reader) {
          throw new Error('No reader available');
        }
  
        const decoder = new TextDecoder();
        let buffer = '';
  
        while (true) {
          const { done, value } = await reader.read();
          
          if (done) {
            onChunk('', true);
            break;
          }
  
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';
  
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = line.slice(6).trim();
              
              if (data === '[DONE]') {
                onChunk('', true);
                return;
              }
  
              try {
                const parsed = JSON.parse(data);
                
                if (parsed.error) {
                  console.error('Server error:', parsed.error);
                  onError(parsed.error);
                  return;
                } 
                else if (parsed.chunk !== undefined) {
                  onChunk(parsed.chunk, false);
                }
              } catch (e) {
                console.error('Error parsing chunk:', e, 'Data:', data);
              }
            }
          }
        }
      })
      .catch(error => {
        if (error.name !== 'AbortError') {
          console.error('Error in streamAnswer:', error);
          onError(error.message || 'Failed to get answer');
        }
      });
  
      return {
        cancel: () => {
          console.log('Cancelling streaming answer');
          controller.abort();
        }
      };
    }
  };
  
  export default qaPipelineService;