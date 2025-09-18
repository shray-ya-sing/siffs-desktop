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

import { AxiosError } from 'axios';

// Type definitions for error responses
export interface ApiErrorDetail {
  message: string;
  context?: string;
  error_type?: string;
  technical_message?: string;
}

export interface ApiErrorResponse {
  detail: ApiErrorDetail | string;
}

// User-friendly fallback messages for different error types
const FALLBACK_ERROR_MESSAGES: Record<string, string> = {
  400: "Invalid request. Please check your input and try again.",
  401: "Authentication required. Please log in.",
  403: "You don't have permission to perform this action.",
  404: "The requested resource was not found.",
  408: "The request took too long. Please try again.",
  429: "Too many requests. Please wait and try again.",
  500: "A server error occurred. Please try again later.",
  503: "The service is currently unavailable. Please try again later.",
};

/**
 * Extract a user-friendly error message from an API error response
 */
export function getErrorMessage(error: unknown): string {
  console.error('API Error:', error); // Log for debugging
  
  // Handle AxiosError (most common case)
  if (error && typeof error === 'object' && 'isAxiosError' in error) {
    const axiosError = error as AxiosError<ApiErrorResponse>;
    
    if (axiosError.response?.data?.detail) {
      const detail = axiosError.response.data.detail;
      
      // If detail is an object with a message, use that
      if (typeof detail === 'object' && 'message' in detail) {
        return detail.message;
      }
      
      // If detail is a string, use that
      if (typeof detail === 'string') {
        return detail;
      }
    }
    
    // Fall back to status-based message
    const status = axiosError.response?.status;
    if (status && FALLBACK_ERROR_MESSAGES[status]) {
      return FALLBACK_ERROR_MESSAGES[status];
    }
    
    // Network error (no response)
    if (axiosError.code === 'ECONNREFUSED' || axiosError.code === 'NETWORK_ERROR') {
      return "Unable to connect to the server. Please check if the application is running.";
    }
    
    // Timeout error
    if (axiosError.code === 'ECONNABORTED') {
      return "The operation took too long. Please try again.";
    }
  }
  
  // Handle fetch errors
  if (error instanceof Error) {
    if (error.name === 'AbortError') {
      return "Operation was cancelled.";
    }
    
    if (error.message.includes('Failed to fetch')) {
      return "Unable to connect to the server. Please try again.";
    }
  }
  
  // Fallback for unknown errors
  return "An unexpected error occurred. Please try again.";
}

/**
 * Log detailed error information for debugging while showing user-friendly messages
 */
export function logErrorDetails(error: unknown, context: string = '', additionalData?: any) {
  const timestamp = new Date().toISOString();
  
  console.group(`❌ Error in ${context || 'Unknown context'} - ${timestamp}`);
  
  if (error && typeof error === 'object' && 'isAxiosError' in error) {
    const axiosError = error as AxiosError;
    
    console.log('Type:', 'Axios Error');
    console.log('Status:', axiosError.response?.status);
    console.log('Status Text:', axiosError.response?.statusText);
    console.log('URL:', axiosError.config?.url);
    console.log('Method:', axiosError.config?.method?.toUpperCase());
    console.log('Response Data:', axiosError.response?.data);
    console.log('Request Headers:', axiosError.config?.headers);
  } else if (error instanceof Error) {
    console.log('Type:', 'JavaScript Error');
    console.log('Name:', error.name);
    console.log('Message:', error.message);
    console.log('Stack:', error.stack);
  } else {
    console.log('Type:', 'Unknown Error');
    console.log('Error:', error);
  }
  
  if (additionalData) {
    console.log('Additional Data:', additionalData);
  }
  
  console.groupEnd();
}

/**
 * Handle API errors in a consistent way across the application
 */
export function handleApiError(
  error: unknown, 
  context: string = '',
  additionalData?: any
): { message: string; shouldRetry: boolean } {
  
  // Log detailed error information for debugging
  logErrorDetails(error, context, additionalData);
  
  // Get user-friendly message
  const message = getErrorMessage(error);
  
  // Determine if the error suggests retrying
  let shouldRetry = false;
  
  if (error && typeof error === 'object' && 'isAxiosError' in error) {
    const axiosError = error as AxiosError;
    const status = axiosError.response?.status;
    
    // Suggest retry for temporary/network issues
    shouldRetry = !status || status >= 500 || status === 408 || status === 429 ||
                  axiosError.code === 'ECONNREFUSED' || 
                  axiosError.code === 'NETWORK_ERROR' ||
                  axiosError.code === 'ECONNABORTED';
  }
  
  return { message, shouldRetry };
}

/**
 * Create a simple error toast notification function (can be customized per UI library)
 */
export function createErrorNotification(message: string, duration: number = 5000) {
  // This is a simple implementation - replace with your toast library
  console.error('User Error:', message);
  
  // You can integrate with your preferred toast notification library here
  // For example: toast.error(message, { duration });
}

/**
 * Simple retry utility for failed operations
 */
export async function retryOperation<T>(
  operation: () => Promise<T>,
  maxRetries: number = 3,
  delayMs: number = 1000
): Promise<T> {
  let lastError: unknown;
  
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      return await operation();
    } catch (error) {
      lastError = error;
      
      // Don't retry on client errors (4xx)
      if (error && typeof error === 'object' && 'isAxiosError' in error) {
        const axiosError = error as AxiosError;
        const status = axiosError.response?.status;
        if (status && status >= 400 && status < 500) {
          throw error; // Don't retry client errors
        }
      }
      
      // Wait before retrying (with exponential backoff)
      if (attempt < maxRetries) {
        const delay = delayMs * Math.pow(2, attempt - 1);
        await new Promise(resolve => setTimeout(resolve, delay));
      }
    }
  }
  
  throw lastError;
}
