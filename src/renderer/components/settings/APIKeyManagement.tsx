import { useState, useEffect } from 'react';
import { 
  Provider, 
  APIKeyStatusResponse, 
  PROVIDER_LABELS, 
  PROVIDER_DESCRIPTIONS,
  PROVIDER_INSTRUCTIONS 
} from '../../types/api-keys';
import { apiKeyService } from '../../services/api-key.service';
import { useToast } from '../ui/use-toast';
import { useAuth } from '../../providers/AuthProvider';

interface APIKeyCardProps {
  provider: Provider;
  isConfigured: boolean;
  hasUserKey: boolean;
  hasEnvKey: boolean;
  onSetKey: (provider: Provider, apiKey: string) => void;
  onRemoveKey: (provider: Provider) => void;
  isLoading: boolean;
}

function APIKeyCard({ 
  provider, 
  isConfigured, 
  hasUserKey, 
  hasEnvKey, 
  onSetKey, 
  onRemoveKey, 
  isLoading 
}: APIKeyCardProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [apiKey, setApiKey] = useState('');
  const [showKey, setShowKey] = useState(false);

  const handleSave = () => {
    if (apiKey.trim()) {
      onSetKey(provider, apiKey.trim());
      setApiKey('');
      setIsEditing(false);
    }
  };

  const handleCancel = () => {
    setApiKey('');
    setIsEditing(false);
  };

  const handleRemove = () => {
    onRemoveKey(provider);
  };

  const getStatusBadge = () => {
    if (hasUserKey) {
      return (
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400">
          ✓ User Key Set
        </span>
      );
    } else if (hasEnvKey) {
      return (
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400">
          ⚙ System Default
        </span>
      );
    } else {
      return (
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400">
          ✗ Not Configured
        </span>
      );
    }
  };

  const openInstructionsLink = () => {
    const url = PROVIDER_INSTRUCTIONS[provider];
    window.open(url, '_blank');
  };

  return (
    <div className="bg-gray-800/50 p-6 rounded-xl border border-gray-700/50 backdrop-blur-sm shadow-lg">
      <div className="flex items-start justify-between mb-4">
        <div>
          <h3 className="text-lg font-light text-white">{PROVIDER_LABELS[provider]}</h3>
          <p className="text-sm text-gray-400 mt-1 font-light">{PROVIDER_DESCRIPTIONS[provider]}</p>
        </div>
        {getStatusBadge()}
      </div>

      {!isEditing ? (
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <button
              onClick={openInstructionsLink}
              className="text-blue-400 hover:text-blue-300 text-sm underline"
            >
              Get API Key →
            </button>
          </div>
          
          <div className="flex gap-2">
            <button
              onClick={() => setIsEditing(true)}
              disabled={isLoading}
              className="bg-gray-800/70 hover:bg-gray-700/80 text-white border border-gray-700/50 px-4 py-2 rounded-full text-sm font-light transition-all duration-300 shadow-lg"
            >
              {hasUserKey ? 'Update Key' : 'Set Key'}
            </button>
            
            {hasUserKey && (
              <button
                onClick={handleRemove}
                disabled={isLoading}
                className="bg-red-900/50 hover:bg-red-800/60 text-white border border-red-700/50 px-4 py-2 rounded-full text-sm font-light transition-all duration-300 shadow-lg"
              >
                Remove Key
              </button>
            )}
          </div>
        </div>
      ) : (
        <div className="space-y-3">
          <div className="space-y-2">
            <label htmlFor={`${provider}-key`} className="text-sm text-gray-300">
              API Key
            </label>
            <div className="relative">
              <input
                id={`${provider}-key`}
                type={showKey ? 'text' : 'password'}
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder={`Enter your ${PROVIDER_LABELS[provider]} API key`}
                className="w-full px-4 py-3 pr-12 bg-gray-800/50 border border-gray-700/50 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-gray-600 focus:ring-2 focus:ring-gray-600/50 transition-all duration-300"
              />
              <button
                type="button"
                onClick={() => setShowKey(!showKey)}
                className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-white"
              >
                {showKey ? '🙈' : '👁️'}
              </button>
            </div>
          </div>
          
          <div className="flex gap-2">
            <button
              onClick={handleSave}
              disabled={isLoading || !apiKey.trim()}
              className="bg-gray-800/70 hover:bg-gray-700/80 disabled:opacity-50 disabled:cursor-not-allowed text-white border border-gray-700/50 px-6 py-2 rounded-full text-sm font-light transition-all duration-300 shadow-lg"
            >
              {isLoading ? 'Saving...' : 'Save Key'}
            </button>
            <button
              onClick={handleCancel}
              disabled={isLoading}
              className="text-gray-400 hover:text-white hover:bg-gray-800/50 px-6 py-2 rounded-full text-sm font-light transition-all duration-300"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export function APIKeyManagement() {
  const [status, setStatus] = useState<APIKeyStatusResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isInitialLoading, setIsInitialLoading] = useState(true);
  const [isConnected, setIsConnected] = useState(true);
  const { toast } = useToast();
  const { user } = useAuth();

  useEffect(() => {
    loadAPIKeyStatus();
  }, [user?.id]); // Reload when user changes

  const loadAPIKeyStatus = async () => {
    try {
      console.log('=== DEBUG: Supabase user object ===');
      console.log('Full user object:', user);
      console.log('User ID:', user?.id);
      console.log('=====================================');
      const statusResponse = await apiKeyService.getAPIKeyStatus(user?.id);
      console.log('API key status response:', statusResponse);
      setStatus(statusResponse);
      setIsInitialLoading(false); // Clear loading state on success
    } catch (error) {
      console.error('Failed to load API key status (backend may be disconnected):', error);
      setIsConnected(false);
      
      // Set a default status to show the form even if backend is disconnected
      const defaultStatus: APIKeyStatusResponse = {
        gemini: {
          has_user_key: false,
          has_env_key: false,
          configured: false
        },
        openai: {
          has_user_key: false,
          has_env_key: false,
          configured: false
        },
        anthropic: {
          has_user_key: false,
          has_env_key: false,
          configured: false
        }
      };
      setStatus(defaultStatus);
    } finally {
      setIsInitialLoading(false);
    }
  };

  const handleSetKey = async (provider: Provider, apiKey: string) => {
    setIsLoading(true);
    try {
      console.log('Setting API key for user:', user?.id);
      await apiKeyService.setAPIKey(provider, apiKey, user?.id);
      await loadAPIKeyStatus(); // Refresh status
      toast({
        title: 'Success',
        description: `${PROVIDER_LABELS[provider]} API key set successfully`
      });
    } catch (error) {
      console.error('Failed to set API key:', error);
      toast({
        title: 'Error',
        description: error instanceof Error ? error.message : 'Failed to set API key',
        variant: 'destructive'
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleRemoveKey = async (provider: Provider) => {
    setIsLoading(true);
    try {
      console.log('Removing API key for user:', user?.id);
      await apiKeyService.removeAPIKey(provider, user?.id);
      await loadAPIKeyStatus(); // Refresh status
      toast({
        title: 'Success',
        description: `${PROVIDER_LABELS[provider]} API key removed successfully`
      });
    } catch (error) {
      console.error('Failed to remove API key:', error);
      toast({
        title: 'Error',
        description: error instanceof Error ? error.message : 'Failed to remove API key',
        variant: 'destructive'
      });
    } finally {
      setIsLoading(false);
    }
  };

  if (isInitialLoading) {
    return (
      <div className="bg-gray-800/50 p-6 rounded-xl border border-gray-700/50 backdrop-blur-sm shadow-lg">
        <div className="animate-pulse">
          <div className="h-6 bg-gray-700 rounded w-1/4 mb-4"></div>
          <div className="space-y-3">
            <div className="h-4 bg-gray-700 rounded w-3/4"></div>
            <div className="h-4 bg-gray-700 rounded w-1/2"></div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="text-center">
        <h2 className="text-2xl font-light text-white mb-2">API Key Management</h2>
        <p className="text-gray-400 font-light">
          Configure your own API keys for AI providers. Setting your own keys allows you to use your own quotas and potentially access newer models.
        </p>
        
        {/* Connection Status Indicator */}
        {!isConnected && (
          <div className="mt-4 p-3 bg-orange-900/30 border border-orange-500/30 rounded-lg">
            <div className="flex items-center justify-center gap-2">
              <div className="w-2 h-2 bg-orange-500 rounded-full animate-pulse"></div>
              <p className="text-orange-300 text-sm font-light">
                Backend disconnected - Settings will be saved when reconnected
              </p>
            </div>
          </div>
        )}
      </div>

      <div className="space-y-4">
        {(['gemini'] as Provider[]).map((provider) => (
          <APIKeyCard
            key={provider}
            provider={provider}
            isConfigured={status?.[provider]?.configured || false}
            hasUserKey={status?.[provider]?.has_user_key || false}
            hasEnvKey={status?.[provider]?.has_env_key || false}
            onSetKey={handleSetKey}
            onRemoveKey={handleRemoveKey}
            isLoading={isLoading}
          />
        ))}
      </div>

      <div className="bg-gray-800/30 border border-gray-700/50 rounded-xl p-4">
        <div className="flex">
          <div className="flex-shrink-0">
            <svg className="h-5 w-5 text-gray-400" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
            </svg>
          </div>
          <div className="ml-3">
            <p className="text-sm text-gray-300 font-light">
              <strong>Note:</strong> Your API keys are stored locally and securely. They are only used to make requests to the respective AI services on your behalf.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
