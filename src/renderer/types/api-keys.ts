// TypeScript interfaces for API key management

export interface APIKeyStatus {
  has_user_key: boolean;
  has_env_key: boolean;
  configured: boolean;
}

export interface APIKeyStatusResponse {
  gemini: APIKeyStatus;
  openai: APIKeyStatus;
  anthropic: APIKeyStatus;
}

export interface SetAPIKeyRequest {
  provider: string;
  api_key: string;
  user_id?: string;
}

export interface APIKeyMessage {
  type: 'SET_API_KEY' | 'GET_API_KEY_STATUS' | 'REMOVE_API_KEY';
  data: any;
  requestId?: string;
}

export interface APIKeyResponse {
  type: 'API_KEY_SET' | 'API_KEY_STATUS' | 'API_KEY_REMOVED' | 'API_KEY_ERROR';
  provider?: string;
  status?: APIKeyStatusResponse;
  message?: string;
  error?: string;
  requestId?: string;
}

export type Provider = 'gemini' | 'openai' | 'anthropic';

export const PROVIDER_LABELS: Record<Provider, string> = {
  gemini: 'Google Gemini',
  openai: 'OpenAI',
  anthropic: 'Anthropic Claude'
};

export const PROVIDER_DESCRIPTIONS: Record<Provider, string> = {
  gemini: 'Google Gemini API for advanced AI conversations and analysis',
  openai: 'OpenAI GPT models for natural language processing',
  anthropic: 'Anthropic Claude models for helpful, harmless, and honest AI'
};

export const PROVIDER_INSTRUCTIONS: Record<Provider, string> = {
  gemini: 'Get your API key from Google AI Studio: https://aistudio.google.com/app/apikey',
  openai: 'Get your API key from OpenAI Platform: https://platform.openai.com/api-keys',
  anthropic: 'Get your API key from Anthropic Console: https://console.anthropic.com/'
};
