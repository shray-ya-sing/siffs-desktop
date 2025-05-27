import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

declare global {
  interface Window {
    electronAPI: {
      log: {
        info: (message: string) => void;
      };
    };
  }
}

export function HomePage() {
  const navigate = useNavigate();

  useEffect(() => {
    // Example of using the exposed electronAPI
    window.electronAPI?.log.info('Home page loaded');
  }, []);

  return (
    <div>
      <h1 className="text-2xl font-bold mb-4">Welcome to the App</h1>
      <p className="mb-4">This is the home page with Electron integration.</p>
      <button
        onClick={() => navigate('/settings')}
        className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
      >
        Go to Settings
      </button>
    </div>
  );
}