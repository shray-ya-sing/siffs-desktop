import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import FolderConnect from '../components/setup/FolderConnect';
import { FileItem } from '../hooks/useFileTree';
import { ConnectionStatus } from '../components/setup/ConnectionStatus';
import { NavIcons } from '../components/navigation/NavIcons';

export function HomePage() {
  const navigate = useNavigate();

  useEffect(() => {
    const electron = (window as any).electron;
    if (electron?.log?.info) {
      electron.log.info('Home page loaded');
    } else {
      console.log('Home page loaded (fallback log)');
    }
  }, []);

  const handleConnect = (files: FileItem[]) => {
    // Navigate to chat with the file tree in state
    navigate('/agent-chat', { state: { files } });
  };

  return (
    <div className="min-h-screen bg-[#0a0a0a] relative">
      {/* Navigation icons */}
      <div className="fixed left-4 top-4 z-50">
        <NavIcons />
      </div>
      <FolderConnect onFolderConnect={handleConnect} />
    </div>
  );
}