/**
 * Service for managing cache operations
 */

const isDev = process.env.NODE_ENV === 'development';
const API_BASE_URL = isDev 
  ? 'http://localhost:3001'
  : 'http://localhost:5001';

export class CacheService {
  /**
   * Clear the metadata cache on the server
   */
  static async clearCache(): Promise<{ success: boolean; message?: string; error?: string }> {
    try {
      console.log('Attempting to clear cache via API:', `${API_BASE_URL}/clear-cache`);
      
      const response = await fetch(`${API_BASE_URL}/clear-cache`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      const data = await response.json();

      if (!response.ok) {
        console.error('Failed to clear cache:', data);
        return {
          success: false,
          error: data.error || 'Failed to clear cache'
        };
      }

      console.log('Cache cleared successfully:', data);
      return {
        success: true,
        message: data.message
      };
    } catch (error) {
      console.error('Error clearing cache:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error occurred'
      };
    }
  }
}
