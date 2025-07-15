import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import FolderConnect from '../components/setup/FolderConnect';
import { FileItem } from '../hooks/useFileTree';
import { ConnectionStatus } from '../components/setup/ConnectionStatus';
import { NavIcons } from '../components/navigation/NavIcons';
import { CacheService } from '../services/cacheService';

export function HomePage() {
  const navigate = useNavigate();

  useEffect(() => {
    const electron = (window as any).electron;
    if (electron?.log?.info) {
      electron.log.info('Home page loaded');
    } else {
      console.log('Home page loaded (fallback log)');
    }

    // Clear cache when HomePage loads to ensure clean state for new folder connections
    const clearCacheOnLoad = async () => {
      try {
        console.log('HomePage: Clearing cache on page load');
        const result = await CacheService.clearCache();
        if (result.success) {
          console.log('HomePage: Cache cleared successfully:', result.message);
        } else {
          console.warn('HomePage: Failed to clear cache:', result.error);
        }
      } catch (error) {
        console.error('HomePage: Error clearing cache:', error);
      }
    };

    clearCacheOnLoad();
  }, []);

  const handleConnect = (files: FileItem[]) => {
    // Navigate to chat with the file tree in state
    navigate('/agent-chat', { state: { files } });
  };

  return (
    <div className="min-h-screen bg-[#0a0a0a] relative">
      <FolderConnect onFolderConnect={handleConnect} />
    </div>
  );
}