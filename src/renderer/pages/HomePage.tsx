import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Sidebar } from '../components/Sidebar';

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
    window.electronAPI?.log.info('Home page loaded');
  }, []);

  return (
    <div className="flex h-screen bg-[#0a0f1a] text-gray-200 font-sans font-thin overflow-hidden">
      {/* Sidebar */}
      <Sidebar />
      
      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <header className="border-b border-[#ffffff0f] p-4 flex justify-between items-center bg-[#1a2035]/20 backdrop-blur-md">
          <h1 className="font-semibold text-lg tracking-wide text-white">Dashboard</h1>
        </header>
        
        {/* Page Content */}
        <main className="flex-1 overflow-y-auto p-6 bg-gradient-to-b from-[#0a0f1a] to-[#1a2035]/30">
          <div className="max-w-4xl mx-auto">
            <div className="bg-[#1a2035]/30 p-6 rounded-lg border border-[#ffffff0f] backdrop-blur-sm shadow-lg">
              <h2 className="text-xl font-semibold mb-4 text-white">Welcome to Your Dashboard</h2>
              <p className="text-white/80">
                You're now logged in and can access the protected content.
              </p>
              
              {/* Keep the existing button but style it to match the theme */}
              <button
                onClick={() => navigate('/settings')}
                className="mt-4 px-4 py-2 bg-blue-600/80 text-white rounded-lg hover:bg-blue-700/80 transition-colors border border-blue-500/30"
              >
                Go to Settings
              </button>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}