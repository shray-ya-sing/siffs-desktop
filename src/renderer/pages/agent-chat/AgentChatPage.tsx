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
import { useEffect, useState, useCallback } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import AIChatUI from '../../components/agent-chat/agent-chat-ui';
import { FileExplorer } from '../../folder-view/FileExplorer';
import { FileItem } from '../../folder-view/FileExplorer';
import { useFileTree } from '../../hooks/useFileTree';
import { webSocketService } from '../../services/websocket/websocket.service';
import WorkspaceHeader from '../../components/workspace/WorkspaceHeader';


export function AgentChatPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  
  // Get initial files from route state or default to empty array
  const initialFiles = (location.state as { files?: FileItem[] })?.files || [];
  const { fileTree, toggleExpand, addFiles } = useFileTree(initialFiles);

  useEffect(() => {
    const electron = (window as any).electron;
    if (electron?.log?.info) {
      electron.log.info('Agent Chat page loaded');
    }

    // Listen for file system updates if needed
    const handleFileSystemUpdate = (data: { files: FileItem[] }) => {
      addFiles(data.files);
    };

    webSocketService.on('FILESYSTEM_UPDATE', handleFileSystemUpdate);

    return () => {
      webSocketService.off('FILESYSTEM_UPDATE', handleFileSystemUpdate);
    };
  }, [addFiles]);

  const handleFileSelect = useCallback((file: FileItem) => {
    console.log('Selected file:', file);
    // Handle file selection (e.g., load file content into chat)
    // You can emit an event or update the chat context here
  }, []);

  const handleFolderConnect = useCallback((files: FileItem[]) => {
    console.log('New folder connected:', files);
    console.log('Current file tree length:', fileTree.length);
    // Add the new folder to the existing file tree
    addFiles(files);
    console.log('addFiles called with:', files);
  }, [addFiles, fileTree.length]);

  const toggleSidebar = useCallback(() => {
    console.log('Toggling sidebar');
    setIsSidebarOpen(prev => !prev);
  }, []);

// Update the main container and sidebar styles in AgentChatPage.tsx
return (
    <div className="flex h-screen bg-[#0a0a0a] text-white overflow-hidden">
      {/* File explorer sidebar */}
      <div className={`
        fixed left-0 top-8 h-[calc(100vh-2rem)] bg-[#0f0f0f]/80 backdrop-blur-sm
        transition-all duration-300 ease-in-out overflow-hidden
        border-r border-gray-700/50
        ${isSidebarOpen ? 'w-72' : 'w-0 pointer-events-none'}
        `}>
        <div className="h-full flex flex-col">
          {/* Sidebar header */}
          <WorkspaceHeader 
            onToggleSidebar={toggleSidebar}
            itemCount={fileTree.length}
            onFolderConnect={handleFolderConnect}
          />
  
          {/* File explorer content */}
          <div className="flex-1 overflow-y-auto">
            <FileExplorer 
              files={fileTree} 
              onFileSelect={handleFileSelect} 
            />
          </div>
  
          {/* Status bar */}
          <div className="p-1.5 text-xs text-gray-400/80 border-t border-gray-700/50">
            {fileTree.length} items
          </div>
        </div>
      </div>
  
      {/* Main chat area */}
      <div className={`flex-1 flex flex-col transition-all duration-300 ${
        isSidebarOpen ? 'ml-72' : 'ml-0'
        } pt-8`}>
        <AIChatUI isSidebarOpen={isSidebarOpen} />
      </div>
  
      {/* Toggle button when sidebar is closed - Add delay to match animation */}
      {!isSidebarOpen && (

        <div className="fixed left-0 top-1/2 -translate-y-1/2 z-50">
        <button
            onClick={toggleSidebar}
            className="bg-gray-800/80 hover:bg-gray-700/80 text-gray-300 p-2 rounded-r-md shadow-lg backdrop-blur-sm"
            aria-label="Show sidebar"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="h-5 w-5"
              viewBox="0 0 20 20"
              fill="currentColor"
            >
              <path
                fillRule="evenodd"
                d="M12.293 5.293a1 1 0 011.414 0l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414-1.414L14.586 11H3a1 1 0 110-2h11.586l-2.293-2.293a1 1 0 010-1.414z"
                clipRule="evenodd"
              />
            </svg>
          </button>
        </div>
      )}
    </div>
  );
}