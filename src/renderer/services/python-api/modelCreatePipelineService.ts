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
// src/renderer/services/python-api/modelCreatePipelineService.ts
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

interface GenerateMetadataParams {
  user_request: string;
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

const modelCreatePipelineService = {
  /**
   * Generate metadata for Excel using LLM
   * @param params Parameters for metadata generation
   * @returns Promise with the generated metadata string
   */
  async generateMetadata(params: GenerateMetadataParams): Promise<string> {
    const response = await apiClient.post('/excel/generate-metadata', {
      user_request: params.user_request,
      model: params.model || 'claude-3-5-sonnet-20241022',
      max_tokens: params.max_tokens || 2000,
      temperature: params.temperature || 0.3,
      stream: params.stream || false,
    });
    
    // Handle both streaming and non-streaming responses
    return params.stream ? response.data : response.data.result;
  },

  /**
   * Parse metadata string into structured format
   * @param params Parameters for metadata parsing
   * @returns Promise with parsed metadata
   */
  async parseMetadata(params: ParseMetadataParams): Promise<any> {
    const response = await apiClient.post('/excel/parse-metadata', {
      metadata: params.metadata,
      strict: params.strict !== false, // Default to true if not specified
    });
    return response.data.data;
  },

  /**
   * Edit Excel file with the provided metadata
   * @param params Parameters for Excel editing
   * @returns Promise with the edit result
   */
  async editExcel(params: EditExcelParams): Promise<PipelineResult> {
    const response = await apiClient.post('/excel/create-excel', {
      file_path: params.file_path,
      metadata: params.metadata,
      visible: params.visible || false,
    });
    return response.data;
  },

  /**
   * Execute the full model creation pipeline
   * @param filePath Path to save the Excel file
   * @param userRequest User's instructions for model creation
   * @param callbacks Callback functions for progress updates
   * @returns Promise that resolves with the pipeline result
   */
  async executePipeline(
    filePath: string,
    userRequest: string,
    callbacks: {
      onProgress?: (step: string, message: string) => void;
      onError?: (error: string) => void;
      onComplete?: (result: PipelineResult) => void;
    } = {}
  ): Promise<PipelineResult> {
    const { onProgress, onError, onComplete } = callbacks;

    try {
      // Step 1: Generate metadata
      onProgress?.('generating', 'Generating metadata...');
      const metadataStr = await this.generateMetadata({
        user_request: userRequest,
        stream: false,
      });

      // Step 2: Parse the generated metadata
      onProgress?.('parsing', 'Parsing metadata...');
      const parsedMetadata = await this.parseMetadata({
        metadata: metadataStr,
        strict: true
      });

      // Step 3: Apply changes to Excel
      onProgress?.('editing', 'Applying changes to Excel file...');
      const result = await this.editExcel({
        file_path: filePath,
        metadata: parsedMetadata,
        visible: false
      });

      onComplete?.(result);
      return result;
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail?.message || 
                         error.response?.data?.detail || 
                         error.message || 
                         'An unknown error occurred';
      
      console.error('Pipeline error:', error);
      onError?.(errorMessage);
      throw new Error(errorMessage);
    }
  },

  /**
   * Stream metadata generation for real-time updates
   * @param userRequest User's instructions for model creation
   * @param onChunk Callback for each chunk of generated metadata
   * @param onError Callback for errors
   */
  async streamMetadataGeneration(
    userRequest: string,
    onChunk: (chunk: string) => void,
    onError: (error: string) => void
  ) {
    try {
      const response = await apiClient.post(
        '/excel/generate-metadata',
        {
          user_request: userRequest,
          stream: true,
        },
        {
          responseType: 'stream',
        }
      );

      // Handle streaming response
      const reader = response.data.getReader();
      const decoder = new TextDecoder();
      
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        const chunk = decoder.decode(value, { stream: true });
        onChunk(chunk);
      }
    } catch (error: any) {
      console.error('Streaming error:', error);
      onError(error.message || 'Error during metadata generation');
    }
  }
};

export default modelCreatePipelineService;