
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
    metadata: any; // Consider defining a more specific type for metadata if possible
    temp_file?: string;
  }

  // Add this interface near your other interfaces
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
     * Extracts metadata from an Excel file.
     * @param filePath The path to the Excel file.
     * @returns A promise that resolves to the extracted metadata.
     */
    extractExcelMetadata(filePath: string): Promise<AxiosResponse<ExcelMetadataResponse>> {
      return apiClient.post<ExcelMetadataResponse>('/excel/extract-metadata', {
        filePath
      });
    },

    /**
     * Analyzes metadata from an Excel file using LLM.
     * @param metadata The metadata to analyze.
     * @param onChunk A callback function to receive chunks of the analysis result.
     * @param onError A callback function to receive error messages.
     * @param model The LLM model to use (default: 'claude-sonnet-4-20250514').
     * @param temperature The sampling temperature (default: 0.3).
     * @returns An object with a cancel function to abort the analysis.
     */
    analyzeExcelMetadata(
      metadata: any,  // or a more specific type if available
      onChunk: (chunk: string, isDone: boolean) => void,
      onError: (error: string) => void,
      model: string = 'claude-sonnet-4-20250514',
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