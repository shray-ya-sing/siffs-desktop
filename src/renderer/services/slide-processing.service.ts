class SlideProcessingService {
  private baseUrl = 'http://localhost:3001/api';

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
