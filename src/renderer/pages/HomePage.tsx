import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Sidebar } from '../components/Sidebar';
import ToolGrid from '../components/tools/ToolGrid';
import { allTools } from '../lib/integrationTools';

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

  return (
    <div className="flex h-screen bg-[#0a0f1a] text-gray-200 font-sans font-thin overflow-hidden">
      <Sidebar />
      
      <div className="flex-1 flex flex-col overflow-hidden">
        <header className="border-b border-[#ffffff0f] p-4 flex justify-between items-center bg-[#1a2035]/20 backdrop-blur-md">
          <h1 className="font-semibold text-lg tracking-wide text-white">Dashboard</h1>
        </header>
        
        <main className="flex-1 overflow-y-auto p-6 bg-gradient-to-b from-[#0a0f1a] to-[#1a2035]/30">
          <div className="max-w-6xl mx-auto space-y-8">
            <div className="bg-[#1a2035]/30 p-6 rounded-lg border border-[#ffffff0f] backdrop-blur-sm shadow-lg">
              <h2 className="text-xl font-semibold mb-4 text-white">Welcome to Cori!</h2>
              <p className="text-white/80 mb-4">
                You're now logged in! You can access the tools below to interact with excel files and models in natural and intuitive ways.
              </p>
              
              <button
                onClick={() => navigate('/settings')}
                className="px-4 py-2 bg-blue-600/80 text-white rounded-lg hover:bg-blue-700/80 transition-colors border border-blue-500/30"
              >
                Go to Settings
              </button>
            </div>

            {/* Tools Grid Section */}
            <div className="bg-[#1a2035]/30 p-6 rounded-lg border border-[#ffffff0f] backdrop-blur-sm shadow-lg">
              <h2 className="text-xl font-semibold mb-6 text-white">Available Tools</h2>
              <ToolGrid tools={allTools} />
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}