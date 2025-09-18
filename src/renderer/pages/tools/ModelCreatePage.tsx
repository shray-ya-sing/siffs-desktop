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
import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Sidebar } from '../../components/Sidebar';
import { ModelCreate } from '../../components/tools/model-create/ModelCreate';

export function ModelCreatePage() {
  const navigate = useNavigate();

  useEffect(() => {
    const electron = (window as any).electron;
    if (electron?.log?.info) {
      electron.log.info('Model Create page loaded');
    } else {
      console.log('Model Create page loaded (fallback log)');
    }
  }, []);

  return (
    <div className="flex h-screen bg-[#0a0f1a] text-gray-200 font-sans font-thin overflow-hidden">
      <Sidebar />
      
      <div className="flex-1 flex flex-col overflow-hidden">
        <header className="border-b border-[#ffffff0f] p-4 flex justify-between items-center bg-[#1a2035]/20 backdrop-blur-md">
          <h1 className="font-semibold text-lg tracking-wide text-white">Create Excel Model</h1>
          <button
            onClick={() => navigate('/')}
            className="text-blue-400 hover:text-blue-300 text-sm"
          >
            ← Back to Dashboard
          </button>
        </header>
        
        <main className="flex-1 overflow-y-auto p-6 bg-gradient-to-b from-[#0a0f1a] to-[#1a2035]/30">
          <div className="max-w-6xl mx-auto">
            <div className="bg-[#1a2035]/30 rounded-lg border border-[#ffffff0f] backdrop-blur-sm shadow-lg">
              <ModelCreate />
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}

export default ModelCreatePage;