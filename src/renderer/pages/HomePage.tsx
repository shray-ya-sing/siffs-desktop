import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import FolderConnect from '../components/setup/FolderConnect';

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

  const handleConnect = () => {
    // Navigate to dashboard or main app after successful connection
    navigate('/agent-chat');
  };

  return (
    <div className="min-h-screen bg-[#0a0a0a]">
      <FolderConnect onConnect={handleConnect} />
    </div>
  );
}