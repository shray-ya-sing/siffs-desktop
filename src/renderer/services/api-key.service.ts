import { webSocketService } from './websocket/websocket.service';
import { v4 as uuidv4 } from 'uuid';
import { 
  APIKeyStatusResponse, 
  SetAPIKeyRequest, 
  Provider, 
  APIKeyResponse 
} from '../types/api-keys';

export class APIKeyService {
  private static instance: APIKeyService;

  private constructor() {}

  public static getInstance(): APIKeyService {
    if (!APIKeyService.instance) {
      APIKeyService.instance = new APIKeyService();
    }
    return APIKeyService.instance;
  }

  /**
   * Set an API key for a provider
   */
  public async setAPIKey(provider: Provider, apiKey: string, userId?: string): Promise<void> {
    return new Promise((resolve, reject) => {
      const requestId = uuidv4();
      
      // Set up response handler
      const handleResponse = (response: APIKeyResponse) => {
        if (response.requestId === requestId) {
          webSocketService.off('API_KEY_SET', handleResponse);
          webSocketService.off('API_KEY_ERROR', handleError);
          resolve();
        }
      };

      const handleError = (response: APIKeyResponse) => {
        if (response.requestId === requestId) {
          webSocketService.off('API_KEY_SET', handleResponse);
          webSocketService.off('API_KEY_ERROR', handleError);
          reject(new Error(response.error || 'Failed to set API key'));
        }
      };

      webSocketService.on('API_KEY_SET', handleResponse);
      webSocketService.on('API_KEY_ERROR', handleError);

      // Send the request
      webSocketService.sendMessage({
        type: 'SET_API_KEY',
        data: {
          provider,
          api_key: apiKey,
          user_id: userId
        },
        requestId
      });
    });
  }

  /**
   * Get API key status for all providers
   */
  public async getAPIKeyStatus(userId?: string): Promise<APIKeyStatusResponse> {
    return new Promise((resolve, reject) => {
      const requestId = uuidv4();
      
      // Set up response handler
      const handleResponse = (response: APIKeyResponse) => {
        if (response.requestId === requestId) {
          webSocketService.off('API_KEY_STATUS', handleResponse);
          webSocketService.off('API_KEY_ERROR', handleError);
          if (response.status) {
            resolve(response.status);
          } else {
            reject(new Error('Invalid response format'));
          }
        }
      };

      const handleError = (response: APIKeyResponse) => {
        if (response.requestId === requestId) {
          webSocketService.off('API_KEY_STATUS', handleResponse);
          webSocketService.off('API_KEY_ERROR', handleError);
          reject(new Error(response.error || 'Failed to get API key status'));
        }
      };

      webSocketService.on('API_KEY_STATUS', handleResponse);
      webSocketService.on('API_KEY_ERROR', handleError);

      // Send the request
      webSocketService.sendMessage({
        type: 'GET_API_KEY_STATUS',
        data: {
          user_id: userId
        },
        requestId
      });
    });
  }

  /**
   * Remove an API key for a provider
   */
  public async removeAPIKey(provider: Provider, userId?: string): Promise<void> {
    return new Promise((resolve, reject) => {
      const requestId = uuidv4();
      
      // Set up response handler
      const handleResponse = (response: APIKeyResponse) => {
        if (response.requestId === requestId) {
          webSocketService.off('API_KEY_REMOVED', handleResponse);
          webSocketService.off('API_KEY_ERROR', handleError);
          resolve();
        }
      };

      const handleError = (response: APIKeyResponse) => {
        if (response.requestId === requestId) {
          webSocketService.off('API_KEY_REMOVED', handleResponse);
          webSocketService.off('API_KEY_ERROR', handleError);
          reject(new Error(response.error || 'Failed to remove API key'));
        }
      };

      webSocketService.on('API_KEY_REMOVED', handleResponse);
      webSocketService.on('API_KEY_ERROR', handleError);

      // Send the request
      webSocketService.sendMessage({
        type: 'REMOVE_API_KEY',
        data: {
          provider,
          user_id: userId
        },
        requestId
      });
    });
  }

  /**
   * Test if an API key is valid (placeholder for future implementation)
   */
  public async testAPIKey(provider: Provider, apiKey: string): Promise<boolean> {
    // This could be implemented later to test API keys before saving
    // For now, we'll just validate that it's not empty
    return apiKey.trim().length > 0;
  }
}

export const apiKeyService = APIKeyService.getInstance();
