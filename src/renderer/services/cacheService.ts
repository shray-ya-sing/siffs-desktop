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
