// src/renderer/pages/tools/ModelQAPage.tsx
import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Sidebar } from '../../components/Sidebar';
import { ModelQA } from '../../components/tools/model-qa/ModelQa';

export function ModelQAPage() {
  const navigate = useNavigate();

  useEffect(() => {
    const electron = (window as any).electron;
    if (electron?.log?.info) {
      electron.log.info('Model QA page loaded');
    } else {
      console.log('Model QA page loaded (fallback log)');
    }
  }, []);

  return (
    <div className="flex h-screen bg-[#0a0f1a] text-gray-200 font-sans font-thin overflow-y-auto">
      <Sidebar />
      
      <div className="flex-1 flex flex-col overflow-hidden">
        <header className="border-b border-[#ffffff0f] p-4 flex justify-between items-center bg-[#1a2035]/20 backdrop-blur-md">
          <h1 className="font-semibold text-lg tracking-wide text-white">Model QA</h1>
          <button
            onClick={() => navigate('/')}
            className="text-blue-400 hover:text-blue-300 text-sm"
          >
            ← Back to Dashboard
          </button>
        </header>
        
        <main className="flex-1 overflow-y-auto p-6 bg-gradient-to-b from-[#0a0f1a] to-[#1a2035]/30">
          <div className="max-w-6xl mx-auto">
            <div className="mx-auto">
              <ModelQA />
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}

export default ModelQAPage;