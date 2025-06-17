// src/renderer/components/connection/ConnectionStatus.tsx
import { useEffect, useState } from 'react';
import { AlertCircle, Wifi, WifiOff, RefreshCw } from 'lucide-react';
import { webSocketService } from '../../services/websocket/websocket.service';
import './styles/ConnectionStatus.css';

export const ConnectionStatus = () => {
  const [status, setStatus] = useState<'connected' | 'disconnected' | 'error'>('disconnected');
  const [isRetrying, setIsRetrying] = useState(false);
  const [lastError, setLastError] = useState<string | null>(null);

  useEffect(() => {
    const handleConnectionChange = (isConnected: boolean) => {
      setStatus(isConnected ? 'connected' : 'disconnected');
      if (isConnected) {
        setLastError(null);
      }
    };

    const handleError = (error: Error) => {
      setStatus('error');
      setLastError(error.message);
    };

    // Subscribe to connection events
    webSocketService.onConnectionChange(handleConnectionChange);
    webSocketService.onError(handleError);

    // Initial status check
    setStatus(webSocketService.serviceIsConnected() ? 'connected' : 'disconnected');

    return () => {
      webSocketService.offConnectionChange(handleConnectionChange);
      webSocketService.offError(handleError);
    };
  }, []);

  const handleRetry = async () => {
    if (isRetrying) return;
    
    setIsRetrying(true);
    try {
      await webSocketService.reconnect();
      // The status will update automatically through the event listeners
    } catch (error) {
      setStatus('error');
      setLastError(error instanceof Error ? error.message : 'Failed to reconnect');
    } finally {
      setIsRetrying(false);
    }
  };

  if (status === 'connected') {
    return null; // Don't show anything when connected
  }

  return (
    <div className={`connection-status ${status}`}>
      <div className="connection-status-content">
        <div className="connection-status-icon">
          {status === 'error' ? (
            <AlertCircle size={20} />
          ) : status === 'disconnected' ? (
            <WifiOff size={20} />
          ) : (
            <Wifi size={20} />
          )}
        </div>
        <div className="connection-status-message">
          {status === 'error'
            ? 'Connection error'
            : 'Disconnected from server'}
          {lastError && <div className="connection-error-detail">{lastError}</div>}
        </div>
        <button
          className="connection-retry-button"
          onClick={handleRetry}
          disabled={isRetrying}
        >
          {isRetrying ? (
            <RefreshCw className="spin" size={16} />
          ) : (
            'Retry'
          )}
        </button>
      </div>
    </div>
  );
};