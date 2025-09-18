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
// src/renderer/components/connection/ConnectionStatus.tsx
import { useEffect, useState } from 'react';
import { AlertCircle, Wifi, WifiOff, RefreshCw, XCircle } from 'lucide-react';
import { webSocketService } from '../../services/websocket/websocket.service';
import './styles/ConnectionStatus.css';

export const ConnectionStatus = () => {
  const [status, setStatus] = useState<'connected' | 'disconnected' | 'error'>('disconnected');
  const [isRetrying, setIsRetrying] = useState(false);
  const [lastError, setLastError] = useState<string | null>(null);
  const [retryTimeout, setRetryTimeout] = useState<NodeJS.Timeout | null>(null);


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

    if (retryTimeout) {
      clearTimeout(retryTimeout);
    }

    // Initial status check
    setStatus(webSocketService.serviceIsConnected() ? 'connected' : 'disconnected');

    return () => {
      webSocketService.offConnectionChange(handleConnectionChange);
      webSocketService.offError(handleError);
    };
  }, [retryTimeout]);

  const handleRetry = async () => {
    if (isRetrying) return;
    
    setIsRetrying(true);
    
    // Clear any existing timeout
    if (retryTimeout) {
      clearTimeout(retryTimeout);
    }
    
    // Set a 30 second timeout
    const timeout = setTimeout(() => {
      setIsRetrying(false);
      setStatus('error');
      setLastError('Connection timed out');
    }, 30000);
    
    setRetryTimeout(timeout);
  
    try {
      await webSocketService.reconnect();
      // Clear the timeout if connection succeeds
      clearTimeout(timeout);
    } catch (error) {
      clearTimeout(timeout);
      setStatus('error');
      setLastError(error instanceof Error ? error.message : 'Failed to reconnect');
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
          ) : retryTimeout ? (
            <XCircle size={16} />
          ) : (
            'Retry'
          )}
        </button>
      </div>
    </div>
  );
};