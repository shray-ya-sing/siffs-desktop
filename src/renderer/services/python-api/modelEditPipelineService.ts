// src/renderer/services/python-api/modelEditPipelineService.ts
import axios, { AxiosInstance, AxiosError } from 'axios';

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

const modelEditPipelineService = {
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
      model: params.model || 'claude-sonnet-4-20250514',
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
   * @param visible Whether to show Excel during editing (default: false)
   * @returns Promise with the edit result
   */
  async applyEdit(filePath: string, metadata: any, visible: boolean = false): Promise<PipelineResult> {
    const response = await apiClient.post('/excel/edit-excel', {
      file_path: filePath,
      metadata: metadata,
      visible
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