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
          
          // After successfully setting the API key, trigger agent initialization
          this.triggerAgentInitialization(provider, userId)
            .then(() => {
              console.log(`Agent initialization triggered for provider: ${provider}`);
              resolve();
            })
            .catch((error) => {
              console.warn(`Failed to trigger agent initialization: ${error.message}`);
              // Still resolve since the API key was set successfully
              resolve();
            });
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
          user_id: userId // Pass the user ID to backend
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
        console.log('=== API_KEY_SERVICE RESPONSE ===');
        console.log('API key status received successfully');
        console.log('Request ID matches:', response.requestId === requestId);
        console.log('==============================');
        
        if (response.requestId === requestId) {
          webSocketService.off('API_KEY_STATUS', handleResponse);
          webSocketService.off('API_KEY_ERROR', handleError);
          if (response.status) {
            resolve(response.status);
          } else {
            console.log('Invalid response format - no status field');
            reject(new Error('Invalid response format'));
          }
        } else {
          console.log('Request ID mismatch - ignoring response');
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
   * Trigger agent initialization after API key is set
   */
  private async triggerAgentInitialization(provider: Provider, userId?: string): Promise<void> {
    // Trigger initialization for all providers since the supervisor agent can use any of them
    if (!['gemini', 'openai', 'anthropic'].includes(provider)) {
      return;
    }

    return new Promise((resolve, reject) => {
      const requestId = uuidv4();
      
      // Set up response handler
      const handleResponse = (response: any) => {
        if (response.requestId === requestId) {
          webSocketService.off('AGENT_INITIALIZATION_SUCCESS', handleResponse);
          webSocketService.off('AGENT_INITIALIZATION_FAILED', handleError);
          console.log('Agent initialization successful:', response.message);
          resolve();
        }
      };

      const handleError = (response: any) => {
        if (response.requestId === requestId) {
          webSocketService.off('AGENT_INITIALIZATION_SUCCESS', handleResponse);
          webSocketService.off('AGENT_INITIALIZATION_FAILED', handleError);
          console.warn('Agent initialization failed:', response.message);
          reject(new Error(response.message || 'Failed to initialize agent'));
        }
      };

      webSocketService.on('AGENT_INITIALIZATION_SUCCESS', handleResponse);
      webSocketService.on('AGENT_INITIALIZATION_FAILED', handleError);

      // Send the initialization request
      webSocketService.sendMessage({
        type: 'INITIALIZE_AGENT_WITH_API_KEY',
        data: {
          user_id: userId
        },
        requestId
      });

      // Set a timeout to avoid hanging forever
      setTimeout(() => {
        webSocketService.off('AGENT_INITIALIZATION_SUCCESS', handleResponse);
        webSocketService.off('AGENT_INITIALIZATION_FAILED', handleError);
        reject(new Error('Agent initialization timeout'));
      }, 10000); // 10 second timeout
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
