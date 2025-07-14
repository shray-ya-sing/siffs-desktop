import { useState, useRef, useEffect } from "react";
import { FolderOpen, FileText, Folder, Check } from "lucide-react";
import FileDiscoveryProgress from "./FileDiscoveryProgress"
import { v4 as uuidv4 } from 'uuid';
import { webSocketService } from '../../services/websocket/websocket.service';
import { fileWatcherService } from '../../services/fileWatcherService';
import { fileProcessingService } from '../../services/fileProcessingService';
import { useNavigate } from "react-router-dom";
import WatermarkLogo from '../logo/WaterMarkLogo'
import MainLogo from '../logo/MainLogo'


  export interface FileItem {
    name: string;
    path: string;
    isDirectory: boolean;
    children?: FileItem[];
    expanded?: boolean;
  }

  interface FolderConnectProps {
    onFolderConnect: (files: FileItem[]) => void;
  }

  
  export default function FolderConnect({ onFolderConnect }: FolderConnectProps) {
    const [isConnecting, setIsConnecting] = useState(false);
    const [discoveryMessages, setDiscoveryMessages] = useState<string[]>([]);
    const [isDiscovering, setIsDiscovering] = useState(false);
    const [clientId] = useState(uuidv4()); // Generate a unique client ID
    const [files, setFiles] = useState<FileItem[]>([]);

    const navigate = useNavigate();

    useEffect(() => {
      const onConnect = () => {
        setDiscoveryMessages(prev => [...prev, "Connected to processing service"]);
      };
    
      const onDisconnect = () => {
        setDiscoveryMessages(prev => [...prev, "Disconnected from processing service"]);
        setIsDiscovering(false);
      };
    
      const onError = (error: any) => {
        console.error('WebSocket error:', error);
        setDiscoveryMessages(prev => [...prev, "Connection error. Please try again."]);
        setIsDiscovering(true);
      };
    
      webSocketService.on('connect', onConnect);
      webSocketService.on('disconnect', onDisconnect);
      webSocketService.on('connect_error', onError);
    
      return () => {
        webSocketService.off('connect', onConnect);
        webSocketService.off('disconnect', onDisconnect);
        webSocketService.off('connect_error', onError);
      };
    }, []);
    
    
    useEffect(() => {
      // Set up WebSocket listeners when component mounts
      const onChunkExtracted = (data: any) => {
        setDiscoveryMessages(prev => [...prev, `Processed chunk from ${data.sheetName}`]);
      };
    
      const onExtractionComplete = (data: any) => {
        setDiscoveryMessages(prev => [...prev, `Extraction complete: ${data.totalChunks} chunks processed`]);
        setIsDiscovering(true);
      };
    
      const onExtractionError = (error: any) => {
        console.error('Extraction error:', error);
        setDiscoveryMessages(prev => [...prev, `Error: ${'Failed to process file'}`]);
        setIsDiscovering(true);
      };
      
      // PowerPoint event handlers
      const onPowerPointExtractionComplete = (data: any) => {
        setDiscoveryMessages(prev => [...prev, `PowerPoint extraction complete: ${data.totalSlides} slides processed`]);
        setIsDiscovering(true);
      };
    
      const onPowerPointExtractionError = (error: any) => {
        console.error('PowerPoint extraction error:', error);
        setDiscoveryMessages(prev => [...prev, `PowerPoint error: ${'Failed to process file'}`]);
        setIsDiscovering(true);
      };
      
      // PDF event handlers
      const onPdfExtractionComplete = (data: any) => {
        setDiscoveryMessages(prev => [...prev, `PDF extraction complete: ${data.totalPages} pages processed`]);
        setIsDiscovering(true);
      };
    
      const onPdfExtractionError = (error: any) => {
        console.error('PDF extraction error:', error);
        setDiscoveryMessages(prev => [...prev, `PDF error: ${'Failed to process file'}`]);
        setIsDiscovering(true);
      };
      
      const onPdfExtractionProgress = (data: any) => {
        setDiscoveryMessages(prev => [...prev, `PDF processing: ${data.message} (${data.progress}%)`]);
      };
      
      // Word event handlers
      const onWordExtractionComplete = (data: any) => {
        setDiscoveryMessages(prev => [...prev, `Word extraction complete: ${data.documentName} processed`]);
        setIsDiscovering(true);
      };
    
      const onWordExtractionError = (error: any) => {
        console.error('Word extraction error:', error);
        setDiscoveryMessages(prev => [...prev, `Word error: ${'Failed to process file'}`]);
        setIsDiscovering(true);
      };
    
      // Register event listeners
      webSocketService.on('CHUNK_EXTRACTED', onChunkExtracted);
      webSocketService.on('EXTRACTION_COMPLETE', onExtractionComplete);
      webSocketService.on('EXTRACTION_ERROR', onExtractionError);
      
      // PowerPoint event listeners
      webSocketService.on('POWERPOINT_EXTRACTION_COMPLETE', onPowerPointExtractionComplete);
      webSocketService.on('POWERPOINT_EXTRACTION_ERROR', onPowerPointExtractionError);
      
      // PDF event listeners
      webSocketService.on('PDF_EXTRACTION_COMPLETE', onPdfExtractionComplete);
      webSocketService.on('PDF_EXTRACTION_ERROR', onPdfExtractionError);
      webSocketService.on('PDF_EXTRACTION_PROGRESS', onPdfExtractionProgress);
      
      // Word event listeners
      webSocketService.on('WORD_EXTRACTION_COMPLETE', onWordExtractionComplete);
      webSocketService.on('WORD_EXTRACTION_ERROR', onWordExtractionError);
    
      // Clean up on unmount
      return () => {
        webSocketService.off('CHUNK_EXTRACTED', onChunkExtracted);
        webSocketService.off('EXTRACTION_COMPLETE', onExtractionComplete);
        webSocketService.off('EXTRACTION_ERROR', onExtractionError);
        
        // PowerPoint cleanup
        webSocketService.off('POWERPOINT_EXTRACTION_COMPLETE', onPowerPointExtractionComplete);
        webSocketService.off('POWERPOINT_EXTRACTION_ERROR', onPowerPointExtractionError);
        
        // PDF cleanup
        webSocketService.off('PDF_EXTRACTION_COMPLETE', onPdfExtractionComplete);
        webSocketService.off('PDF_EXTRACTION_ERROR', onPdfExtractionError);
        webSocketService.off('PDF_EXTRACTION_PROGRESS', onPdfExtractionProgress);
        
        // Word cleanup
        webSocketService.off('WORD_EXTRACTION_COMPLETE', onWordExtractionComplete);
        webSocketService.off('WORD_EXTRACTION_ERROR', onWordExtractionError);
      };
    }, [onFolderConnect]);


    
    const processDirectory = async (fullPath: string, dirName: string, watchPath: string) => {
      setIsConnecting(true);
      setIsDiscovering(true);
      setDiscoveryMessages(prev => [...prev, "Scanning directory..."]);
    
      try {
        // Scan the directory using IPC call to main process
        const electron = (window as any).electron;
        if (!electron?.ipcRenderer) {
          throw new Error('Electron IPC not available');
        }
        
        // Request file scanning from main process
        const scanResult = await electron.ipcRenderer.invoke('fs:scan-directory', fullPath);
        
        if (!scanResult.success) {
          throw new Error(scanResult.error || 'Failed to scan directory');
        }
        
        const fileList: FileItem[] = scanResult.files;
        
        setDiscoveryMessages(prev => [...prev, `Selected directory: ${fullPath}`]);
        setDiscoveryMessages(prev => [...prev, `Found ${fileList.length} files and folders`]);
        console.log("Processing directory:", fullPath);
        
        // Filter Excel, PowerPoint, and PDF files
        const excelFiles = fileList.filter(file => 
          !file.isDirectory && (file.name.endsWith('.xlsx') || file.name.endsWith('.xls'))
        );
        
        const powerPointFiles = fileList.filter(file => 
          !file.isDirectory && (file.name.endsWith('.pptx') || file.name.endsWith('.ppt'))
        );
        
        const pdfFiles = fileList.filter(file => 
          !file.isDirectory && file.name.endsWith('.pdf')
        );
        
        // Filter Word files
        const wordFiles = fileList.filter(file => 
          !file.isDirectory && file.name.endsWith('.docx')
        );
        
        const allSupportedFiles = [...excelFiles, ...powerPointFiles, ...pdfFiles, ...wordFiles];
        
        if (allSupportedFiles.length === 0) {
          setDiscoveryMessages(prev => [...prev, "No supported files (.xlsx, .pptx, .pdf, .docx) found in the selected directory"]);
        } else {
          setDiscoveryMessages(prev => [...prev, `Found ${allSupportedFiles.length} supported files`]);
        }
    
        // Trigger extraction for each supported file
        for (const file of allSupportedFiles) {
          const message = `Processing file: ${file.name}`;
          setDiscoveryMessages(prev => [...prev, message]);
          
          try {
            // Get file content from main process
            const fileResult = await electron.ipcRenderer.invoke('fs:read-file', 
              `${fullPath}/${file.path}`
            );
            
            if (!fileResult.success) {
              throw new Error(fileResult.error || 'Failed to read file');
            }
            
            const base64Content = fileResult.content;
            const requestId = uuidv4();

            // Debug log
            console.log('Sending file for extraction:', {
              client_id: clientId,
              request_id: requestId,
              file_path: `${dirName}/${file.path}`,
              file_content: base64Content ? `[${base64Content.length} chars]` : 'EMPTY'
            });
            
            // Determine file type and send appropriate extraction request
            const isExcelFile = file.name.endsWith('.xlsx') || file.name.endsWith('.xls');
            const isPowerPointFile = file.name.endsWith('.pptx') || file.name.endsWith('.ppt');
            const isPdfFile = file.name.endsWith('.pdf');
            const isWordFile = file.name.endsWith('.docx');
            
            if (isExcelFile) {
              // Send Excel extraction request
              webSocketService.emit('EXTRACT_METADATA', {
                client_id: clientId,
                request_id: requestId,
                file_path: `${dirName}/${file.path}`,
                file_content: base64Content
              });
            } else if (isPowerPointFile) {
              // Send PowerPoint extraction request
              webSocketService.emit('EXTRACT_POWERPOINT_METADATA', {
                client_id: clientId,
                request_id: requestId,
                file_path: `${dirName}/${file.path}`,
                file_content: base64Content
              });
            } else if (isPdfFile) {
              // Send PDF extraction request
              webSocketService.emit('EXTRACT_PDF_CONTENT', {
                client_id: clientId,
                request_id: requestId,
                file_path: `${dirName}/${file.path}`,
                file_content: base64Content,
                include_images: true,
                include_tables: true,
                include_forms: true,
                ocr_images: false
              });
            } else if (isWordFile) {
              // Send Word extraction request
              webSocketService.emit('EXTRACT_WORD_METADATA', {
                client_id: clientId,
                request_id: requestId,
                file_path: `${dirName}/${file.path}`,
                file_content: base64Content
              });
            }
    
            // Small delay between files
            await new Promise(resolve => setTimeout(resolve, 300));
          } catch (fileError) {
            console.error(`Error processing file ${file.name} at ${file.path}:`, fileError);
            setDiscoveryMessages(prev => [...prev, `Error processing ${file.name}: ${fileError}`]);
          }
        }

        // Build file tree
        const fileTree = buildFileTree(fileList);
        console.log("File tree:", fileTree);
        setFiles(fileTree);
        
        // Set up file processing context for automatic processing
        fileProcessingService.setProcessingContext({
          workspacePath: fullPath,
          clientId: clientId,
          workspaceName: dirName
        });
        
        // Start file watcher for the directory
        try {
          console.log('FolderConnect: Starting file watcher for directory:', dirName);
          console.log('FolderConnect: Watch path:', watchPath);
          console.log('FolderConnect: File watcher service available:', !!fileWatcherService);
          
          // Attempt to start file watcher using the actual file system path
          const watcherResult = await fileWatcherService.startWatching(watchPath);
          console.log('FolderConnect: File watcher result:', watcherResult);
          
          if (watcherResult.success) {
            setDiscoveryMessages(prev => [...prev, "✅ File monitoring started successfully"]);
            setDiscoveryMessages(prev => [...prev, "✅ Automatic file processing enabled"]);
            console.log('FolderConnect: File watcher started successfully for path:', watcherResult.watchedPath);
          } else {
            setDiscoveryMessages(prev => [...prev, `⚠️ File monitoring could not be started: ${watcherResult.error}`]);
            console.error('FolderConnect: Failed to start file watcher:', watcherResult.error);
          }
        } catch (watcherError) {
          console.error('FolderConnect: Exception while starting file watcher:', watcherError);
          setDiscoveryMessages(prev => [...prev, "⚠️ Warning: File monitoring could not be started"]);
        }
        
        // Call onConnect with the files
        onFolderConnect(fileTree);
    
      } catch (error) {
        console.error('Error processing directory:', error);
        setDiscoveryMessages(prev => [...prev, "Error processing directory"]);
        setIsDiscovering(true);
      }
    };
    

    // Helper function to build the file tree
    const buildFileTree = (files: FileItem[]): FileItem[] => {
      const fileMap: Record<string, FileItem> = {};
      const tree: FileItem[] = [];

      // First pass: Create a map of all files/directories
      files.forEach(file => {
        fileMap[file.path] = { ...file, children: [] };
      });

      // Second pass: Build the tree
      files.forEach(file => {
        const pathParts = file.path.split('/');
        if (pathParts.length > 1) {
          const parentPath = pathParts.slice(0, -1).join('/');
          if (fileMap[parentPath]) {
            fileMap[parentPath].children = fileMap[parentPath].children || [];
            fileMap[parentPath].children?.push(fileMap[file.path]);
          }
        } else {
          tree.push(fileMap[file.path]);
        }
      });

      return tree;
    };

  
    const handleOpenFolder = async () => {
      setIsConnecting(true);
      setIsDiscovering(true);
      setDiscoveryMessages([]);
    
      try {
        // Use Electron's native dialog instead of File System Access API
        const electron = (window as any).electron;
        if (!electron?.ipcRenderer) {
          throw new Error('Electron IPC not available');
        }
        
        const result = await electron.ipcRenderer.invoke('dialog:show-directory-picker');
        
        if (!result.success) {
          if (result.canceled) {
            console.log("User cancelled folder selection");
          } else {
            console.error("Dialog error:", result.error);
          }
          setIsConnecting(false);
          setIsDiscovering(false);
          return;
        }
        
        // We now have the actual file system path!
        const fullPath = result.path;
        const dirName = result.name;
        
        await processDirectory(fullPath, dirName, fullPath);
      } catch (err) {
        console.error("Error opening folder:", err);
        setIsConnecting(false);
        setIsDiscovering(false);
      }
    };

  
    return (
      <div
        className={`flex flex-col items-center justify-center min-h-screen text-white relative overflow-hidden`}
        style={{ backgroundColor: "#0a0a0a" }}
      >
        {/* Background elements */}
        <div
          className="absolute inset-0 pointer-events-none"
          style={{
            background: `radial-gradient(circle at center, rgba(20, 20, 20, 0.3) 0%, rgba(10, 10, 10, 0.8) 40%, rgba(10, 10, 10, 1) 70%)`,
            zIndex: 1,
          }}
        />
        <WatermarkLogo />
  
        {/* Main content */}
        <div className="relative z-10 text-center space-y-8 animate-fade-in">
          {/* Logo and Title */}
          <div className="space-y-4">
            <MainLogo />
            <div className="space-y-1">
              <h1 className="text-5xl font-bold text-gray-100 tracking-wide">Volute</h1>
              <h2 className="text-xl font-light text-gray-300">Workspaces</h2>
            </div>
          </div>
  
          <div className="flex justify-center">
            <button
              onClick={handleOpenFolder}
              disabled={isConnecting}
              className="flex items-center gap-2 px-5 py-2.5 rounded-3xl text-sm font-medium transition-all duration-200 hover:scale-105 hover:shadow-lg disabled:opacity-50 disabled:cursor-not-allowed"
              style={{
                background: "linear-gradient(135deg, #2a2a2a 0%, #1a1a1a 100%)",
                border: "1px solid #333333",
                color: "#e5e5e5",
              }}
            >
              {isConnecting ? (
                <>
                  <div className="w-4 h-4 border-2 border-gray-400 border-t-transparent rounded-full animate-spin" />
                  Opening Workspace...
                </>
              ) : (
                <>
                  <FolderOpen size={16} />
                  Open Folder
                </>
              )}
            </button>
          </div>
  
          {/* Instructions */}
          <div className="max-w-md mx-auto text-center">
            <p className="text-sm text-gray-500 leading-relaxed">
              Select a folder to copy it to the agent workspace. Volute reads Excel (.xlsx), PowerPoint (.pptx, .ppt), PDF (.pdf), and Word (.docx) files, so any other file types will be ignored.
            </p>
          </div>
        </div>
  
        {/* File discovery progress */}
        <FileDiscoveryProgress 
          messages={discoveryMessages} 
          isActive={isDiscovering} 
        />
      </div>
    );
  }