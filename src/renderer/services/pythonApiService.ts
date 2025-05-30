
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
    withCredentials: true,
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

    // New Excel metadata extraction endpoint
    extractExcelMetadata(filePath: string): Promise<AxiosResponse<ExcelMetadataResponse>> {
      return apiClient.post<ExcelMetadataResponse>('/excel/extract-metadata', {
        filePath
      });
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