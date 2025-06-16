import { useEffect, useState, useCallback } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import AIChatUI from '../../components/agent-chat/agent-chat-ui';
import { FileExplorer } from '../../folder-view/FileExplorer';
import { FileItem } from '../../folder-view/FileExplorer';
import { useFileTree } from '../../hooks/useFileTree';
import { webSocketService } from '../../services/websocket/websocket.service';
import { NavIcons } from '../../components/navigation/NavIcons';


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

  const toggleSidebar = useCallback(() => {
    setIsSidebarOpen(prev => !prev);
  }, []);

  // Update the main container and sidebar styles in AgentChatPage.tsx
return (
    <div className="flex h-screen bg-[#0a0a0a] text-white overflow-hidden pt-[5%]">
      {/* Navigation icons */}
      <div className="fixed left-4 top-4 z-50">
        <NavIcons />
      </div>
      {/* File explorer sidebar */}
      <div className={`
        fixed left-0 top-0 h-[95%] bg-[#0f0f0f]/80 backdrop-blur-sm
        transition-all duration-300 ease-in-out overflow-hidden
        border-r border-gray-700/50 mt-[5%]
        ${isSidebarOpen ? 'w-72' : 'w-0'}
        `}>
        <div className="h-full flex flex-col">
          {/* Sidebar header */}
          <div className="flex items-center justify-between p-3 border-b border-gray-700/50">
            <h2 className="text-base font-medium text-gray-200">Workspace</h2>
            <button
              onClick={toggleSidebar}
              className="p-1 rounded-md hover:bg-gray-700/50 text-gray-400 hover:text-gray-200"
              aria-label="Toggle sidebar"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className="h-5 w-5"
                viewBox="0 0 20 20"
                fill="currentColor"
              >
                <path
                  fillRule="evenodd"
                  d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                  clipRule="evenodd"
                />
              </svg>
            </button>
          </div>
  
          {/* File explorer content */}
          <div className="flex-1 overflow-y-auto">
            <FileExplorer 
              files={fileTree} 
              onFileSelect={handleFileSelect} 
            />
          </div>
  
          {/* Status bar */}
          <div className="p-1.5 text-xs text-gray-400/80 border-t border-gray-700/50">  // More subtle text
            {fileTree.length} items
          </div>
        </div>
      </div>
  
      {/* Main chat area */}
      <div className={`flex-1 flex flex-col transition-all duration-300 ${
        isSidebarOpen ? 'ml-72' : 'ml-0'
        } mt-[5%]`}>
        <AIChatUI />
      </div>
  
      {/* Toggle button when sidebar is closed */}
      {!isSidebarOpen && (
        <button
          onClick={toggleSidebar}
          className="fixed left-0 top-1/2 -translate-y-1/2 bg-gray-800/80 hover:bg-gray-700/80 text-gray-300 p-2 rounded-r-md shadow-lg backdrop-blur-sm"
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
      )}
    </div>
  );
}