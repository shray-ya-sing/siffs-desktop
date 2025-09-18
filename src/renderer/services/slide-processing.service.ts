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
class SlideProcessingService {
  private baseUrl: string;

  constructor() {
    const isDev = process.env.NODE_ENV === 'development';
    this.baseUrl = isDev ? 'http://localhost:3001/api' : 'http://localhost:5001/api';
  }

  async processFolderIndex(folderPath: string): Promise<any> {
    try {
      console.log('Frontend: Sending folder path:', folderPath);
      console.log('Frontend: Path type:', typeof folderPath);
      console.log('Frontend: Path repr:', JSON.stringify(folderPath));
      
      const requestBody = {
        folder_path: folderPath
      };
      
      console.log('Frontend: Request body:', requestBody);
      console.log('Frontend: JSON stringified:', JSON.stringify(requestBody));
      
      const response = await fetch(`${this.baseUrl}/slides/process-folder`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody)
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
      }

      const result = await response.json();
      console.log('Folder processing result:', result);
      return result;

    } catch (error) {
      console.error('Error processing folder:', error);
      throw error;
    }
  }

  async getProcessingStatus(): Promise<any> {
    try {
      const response = await fetch(`${this.baseUrl}/slides/processing-status`);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error getting processing status:', error);
      throw error;
    }
  }

  async getSlideStats(): Promise<any> {
    try {
      const response = await fetch(`${this.baseUrl}/slides/stats`);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error getting slide stats:', error);
      throw error;
    }
  }

  async clearAllSlides(): Promise<any> {
    try {
      const response = await fetch(`${this.baseUrl}/slides/clear-all`, {
        method: 'POST',
      });
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error clearing slides:', error);
      throw error;
    }
  }
}

export const slideProcessingService = new SlideProcessingService();
