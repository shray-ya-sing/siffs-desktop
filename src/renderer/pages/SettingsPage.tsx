import React, { useState, useEffect } from 'react';
import { FolderOpen, Check, Loader2, ArrowRight } from 'lucide-react';
import { slideProcessingService } from '../services/slide-processing.service';

export function SettingsPage() {
  const [folderPath, setFolderPath] = useState<string>('');
  const [connectedFolder, setConnectedFolder] = useState<string | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<'disconnected' | 'connecting' | 'connected'>('disconnected');
  const [isIndexing, setIsIndexing] = useState(false);
  const [indexingStatus, setIndexingStatus] = useState<string>('');
  const [indexingResults, setIndexingResults] = useState<any>(null);

  // Check for existing folder connection on component mount
  useEffect(() => {
    // This could be persisted in localStorage or fetched from your backend
    const savedFolder = localStorage.getItem('connectedFolder');
    if (savedFolder) {
      setConnectedFolder(savedFolder);
      setConnectionStatus('connected');
      setFolderPath(savedFolder);
    }
  }, []);

  const handleSubmitFolder = async () => {
    if (!folderPath.trim()) {
      setIndexingStatus('Please enter a folder path');
      return;
    }

    setConnectionStatus('connecting');
    setIsIndexing(true);
    setIndexingStatus('Starting indexing process...');
    setIndexingResults(null);

    try {
      console.log('Starting folder indexing for:', folderPath);
      
      const result = await slideProcessingService.processFolderIndex(folderPath);
      
      console.log('Indexing completed:', result);
      setIndexingResults(result);
      setIndexingStatus(`Successfully indexed ${result.files_processed} files with ${result.slides_processed} slides`);
      
      // Save the connected folder path
      setConnectedFolder(folderPath);
      setConnectionStatus('connected');
      
      // Persist the connection
      localStorage.setItem('connectedFolder', folderPath);
      localStorage.setItem('connectedFolderName', getFolderDisplayName(folderPath));
      
    } catch (error) {
      console.error('Indexing failed:', error);
      setIndexingStatus(`Indexing failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
      setConnectionStatus('disconnected');
    } finally {
      setIsIndexing(false);
    }
  };

  const handleDisconnectFolder = () => {
    setConnectedFolder(null);
    setConnectionStatus('disconnected');
    setFolderPath('');
    setIndexingResults(null);
    setIndexingStatus('');
    localStorage.removeItem('connectedFolder');
    localStorage.removeItem('connectedFolderName');
  };

  const getFolderDisplayName = (path: string) => {
    return localStorage.getItem('connectedFolderName') || path.split(/[\\\/]/).pop() || path;
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFolderPath(e.target.value);
    // Clear any previous error messages
    if (indexingStatus && indexingStatus.includes('failed')) {
      setIndexingStatus('');
    }
  };

  const handleReIndexFolder = async () => {
    if (!connectedFolder) {
      console.error('No folder connected');
      return;
    }

    setIsIndexing(true);
    setIndexingStatus('Re-indexing folder...');
    setIndexingResults(null);

    try {
      console.log('Re-indexing folder:', connectedFolder);
      
      const result = await slideProcessingService.processFolderIndex(connectedFolder);
      
      console.log('Re-indexing completed:', result);
      setIndexingResults(result);
      setIndexingStatus(`Successfully re-indexed ${result.files_processed} files with ${result.slides_processed} slides`);
      
    } catch (error) {
      console.error('Re-indexing failed:', error);
      setIndexingStatus(`Re-indexing failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setIsIndexing(false);
    }
  };

  return (
    <>
      {/* Embedded styles to match the morphism theme */}
      <style>{`
        .settings-page {
          margin: 0;
          padding: 0;
          box-sizing: border-box;
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Helvetica Neue', sans-serif;
          overflow: hidden;
          width: 100vw;
          height: calc(100vh - 32px);
          margin-top: 32px;
          background: linear-gradient(135deg, 
            #F8F9FA 0%, 
            #F5F6F8 25%, 
            #F2F4F6 50%, 
            #EFF1F4 75%, 
            #ECEEF2 100%
          );
          display: flex;
          align-items: center;
          justify-content: center;
          position: relative;
        }

        /* Add subtle morphism background elements */
        .settings-page::before {
          content: '';
          position: absolute;
          top: 20%;
          left: 15%;
          width: 200px;
          height: 200px;
          background: rgba(255, 255, 255, 0.4);
          border-radius: 50%;
          filter: blur(60px);
          animation: settings-float 6s ease-in-out infinite;
        }

        .settings-page::after {
          content: '';
          position: absolute;
          bottom: 20%;
          right: 15%;
          width: 150px;
          height: 150px;
          background: rgba(255, 255, 255, 0.3);
          border-radius: 50%;
          filter: blur(40px);
          animation: settings-float 8s ease-in-out infinite reverse;
        }

        @keyframes settings-float {
          0%, 100% {
            transform: translateY(0px) scale(1);
          }
          50% {
            transform: translateY(-20px) scale(1.1);
          }
        }

        .settings-container {
          position: relative;
          z-index: 10;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          gap: 3rem;
          width: 100%;
          max-width: 600px;
          margin: 0 auto;
          padding: 2rem;
        }

        .settings-title {
          font-size: 2.5rem;
          font-weight: 300;
          color: #4a5568;
          margin-bottom: 0.5rem;
          text-align: center;
        }

        .settings-subtitle {
          font-size: 1.1rem;
          color: #718096;
          text-align: center;
          margin-bottom: 0;
          max-width: 500px;
          line-height: 1.6;
        }

        .connect-button {
          display: inline-flex;
          align-items: center;
          gap: 0.75rem;
          padding: 16px 32px;
          font-size: 16px;
          font-weight: 500;
          border: none;
          border-radius: 50px;
          background: rgba(255, 255, 255, 0.7);
          backdrop-filter: blur(10px);
          -webkit-backdrop-filter: blur(10px);
          box-shadow: 
            0 8px 32px rgba(0, 0, 0, 0.08),
            inset 0 1px 0 rgba(255, 255, 255, 0.9),
            inset 0 -1px 0 rgba(255, 255, 255, 0.5);
          color: #4a5568;
          outline: none;
          transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
          border: 1px solid rgba(255, 255, 255, 0.6);
          cursor: pointer;
        }

        .folder-input-container {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          width: 100%;
          max-width: 500px;
          margin: 0 auto;
        }

        .folder-input {
          flex: 1;
          padding: 12px 16px;
          font-size: 14px;
          border: 1px solid rgba(255, 255, 255, 0.3);
          border-radius: 24px;
          background: rgba(255, 255, 255, 0.5);
          backdrop-filter: blur(10px);
          -webkit-backdrop-filter: blur(10px);
          color: #4a5568;
          outline: none;
          transition: all 0.2s ease;
        }

        .folder-input:focus {
          border-color: rgba(59, 130, 246, 0.5);
          box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
        }

        .folder-input::placeholder {
          color: #9ca3af;
        }

        .submit-button {
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 12px;
          border: none;
          border-radius: 50%;
          background: rgba(59, 130, 246, 0.8);
          color: white;
          cursor: pointer;
          transition: all 0.2s ease;
          width: 44px;
          height: 44px;
        }

        .submit-button:hover {
          background: rgba(59, 130, 246, 1);
          transform: translateX(2px);
        }

        .submit-button:disabled {
          opacity: 0.6;
          cursor: not-allowed;
          transform: none;
        }

        .connect-button:hover {
          background: rgba(255, 255, 255, 0.8);
          transform: translateY(-2px);
          box-shadow: 
            0 12px 40px rgba(0, 0, 0, 0.12),
            inset 0 1px 0 rgba(255, 255, 255, 0.9),
            inset 0 -1px 0 rgba(255, 255, 255, 0.5);
        }

        .connect-button:active {
          transform: translateY(0px);
        }

        .connect-button:disabled {
          opacity: 0.6;
          cursor: not-allowed;
          transform: none;
        }

        .connected-info {
          background: rgba(34, 197, 94, 0.1);
          border: 1px solid rgba(34, 197, 94, 0.2);
          border-radius: 16px;
          padding: 1rem;
          margin-top: 1rem;
          color: #059669;
        }

        .disconnect-button {
          background: rgba(239, 68, 68, 0.1);
          color: #dc2626;
          border: 1px solid rgba(239, 68, 68, 0.2);
          padding: 8px 16px;
          border-radius: 24px;
          font-size: 14px;
          margin-top: 0.5rem;
          cursor: pointer;
          transition: all 0.2s ease;
        }

        .disconnect-button:hover {
          background: rgba(239, 68, 68, 0.2);
        }

        .spinner {
          width: 20px;
          height: 20px;
          border: 2px solid #e2e8f0;
          border-top: 2px solid #4a5568;
          border-radius: 50%;
          animation: spin 1s linear infinite;
        }

        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>

      <div className="settings-page">
        <div className="settings-container">
          <div style={{ textAlign: 'center' }}>
            <h1 className="settings-title">Settings</h1>
            <p className="settings-subtitle">
              Connect a folder to give Siffs access to your files. 
              Siffs only supports search on PowerPoint (.pptx) files, all other files will be ignored.
            </p>
          </div>

          <div style={{ textAlign: 'center', width: '100%' }}>
            {connectionStatus === 'connected' && connectedFolder ? (
              <div>
                <div className="connected-info">
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', justifyContent: 'center' }}>
                    <Check size={20} />
                    <span style={{ fontWeight: '500' }}>Connected</span>
                  </div>
                  <div style={{ marginTop: '0.5rem', fontSize: '0.9rem' }}>
                    {getFolderDisplayName(connectedFolder)}
                  </div>
                  
                  {/* Re-indexing Section */}
                  <div style={{ marginTop: '1rem', textAlign: 'center' }}>
                    <button
                      className="connect-button"
                      onClick={handleReIndexFolder}
                      disabled={isIndexing}
                      style={{ 
                        backgroundColor: isIndexing ? 'rgba(156, 163, 175, 0.5)' : undefined,
                        cursor: isIndexing ? 'not-allowed' : 'pointer'
                      }}
                    >
                      {isIndexing ? (
                        <>
                          <Loader2 size={20} className="animate-spin" />
                          Processing...
                        </>
                      ) : (
                        <>
                          <FolderOpen size={20} />
                          Re-Index Slides
                        </>
                      )}
                    </button>
                    
                    {indexingStatus && (
                      <div style={{ 
                        marginTop: '1rem', 
                        fontSize: '0.9rem',
                        color: indexingStatus.includes('failed') ? '#dc2626' : '#059669'
                      }}>
                        {indexingStatus}
                      </div>
                    )}
                    
                    {indexingResults && (
                      <div style={{ 
                        marginTop: '1rem', 
                        fontSize: '0.8rem',
                        color: '#6b7280'
                      }}>
                        Files: {indexingResults.files_processed} | Slides: {indexingResults.slides_processed}
                        {indexingResults.failed_files?.length > 0 && (
                          <div style={{ color: '#f59e0b' }}>
                            {indexingResults.failed_files.length} files failed to process
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                  
                  <button 
                    className="disconnect-button"
                    onClick={handleDisconnectFolder}
                  >
                    Disconnect
                  </button>
                </div>
              </div>
            ) : (
              <div style={{ width: '100%' }}>
                <div className="folder-input-container">
                  <input
                    type="text"
                    className="folder-input"
                    placeholder="Enter folder path (e.g., C:\Documents\Presentations)"
                    value={folderPath}
                    onChange={handleInputChange}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && !isIndexing && folderPath.trim()) {
                        handleSubmitFolder();
                      }
                    }}
                    disabled={isIndexing}
                  />
                  <button
                    className="submit-button"
                    onClick={handleSubmitFolder}
                    disabled={isIndexing || !folderPath.trim()}
                    title="Index folder"
                  >
                    {isIndexing ? (
                      <Loader2 size={20} className="animate-spin" />
                    ) : (
                      <ArrowRight size={20} />
                    )}
                  </button>
                </div>
                
                {indexingStatus && (
                  <div style={{ 
                    marginTop: '1rem', 
                    fontSize: '0.9rem',
                    color: indexingStatus.includes('failed') || indexingStatus.includes('Please enter') ? '#dc2626' : '#059669'
                  }}>
                    {indexingStatus}
                  </div>
                )}
                
                {indexingResults && (
                  <div style={{ 
                    marginTop: '1rem', 
                    fontSize: '0.8rem',
                    color: '#6b7280'
                  }}>
                    Files: {indexingResults.files_processed} | Slides: {indexingResults.slides_processed}
                    {indexingResults.failed_files?.length > 0 && (
                      <div style={{ color: '#f59e0b' }}>
                        {indexingResults.failed_files.length} files failed to process
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
