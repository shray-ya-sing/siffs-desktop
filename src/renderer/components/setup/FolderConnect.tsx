import { useState, useRef, useEffect } from "react";
import { FolderOpen, FileText, Folder, Check } from "lucide-react";
import FileDiscoveryProgress from "./FileDiscoveryProgress"
import { v4 as uuidv4 } from 'uuid';
import { webSocketService } from '../../services/websocket/websocket.service';
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


    const scanDirectory = async (dirHandle: any, fileList: FileItem[] = [], path: string[] = []) => {
      try {
        // @ts-ignore - TypeScript doesn't have types for File System Access API
        for await (const entry of dirHandle.values()) {
          const entryPath = [...path, entry.name];
          
          if (entry.kind === 'file') {
            fileList.push({
              name: entry.name,
              path: entryPath.join('/'),
              isDirectory: false
            });
          } else if (entry.kind === 'directory') {
            // Add directory to the list
            fileList.push({
              name: entry.name,
              path: entryPath.join('/'),
              isDirectory: true
            });
            
            // Recursively scan subdirectories
            await scanDirectory(entry, fileList, entryPath);
          }
        }
      } catch (error) {
        console.error('Error scanning directory:', error);
        throw error;
      }
    };
    
    const processDirectory = async (dirHandle: any, dirName: string) => {
      setIsConnecting(true);
      setIsDiscovering(true);
      setDiscoveryMessages(prev => [...prev, "Scanning directory..."]);
    
      try {
        const fileList: FileItem[] = [];
        await scanDirectory(dirHandle, fileList, []);
        console.log("File list:", fileList);
        
        // Filter Excel, PowerPoint, and PDF files
        const excelFiles = fileList.filter(file => 
          !file.isDirectory && file.name.endsWith('.xlsx')
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
          setDiscoveryMessages(prev => [...prev, "No Excel, PowerPoint, or PDF files found in the selected directory"]);
          return;
        }
    
        // Trigger extraction for each supported file
        for (const file of allSupportedFiles) {
          const message = `Found file: ${file.name}`;
          setDiscoveryMessages(prev => [...prev, message]);
          
          try {
            // Get file content as ArrayBuffer
            const fileHandle = await dirHandle.getFileHandle(file.name);
            const fileContent = await fileHandle.getFile();
            const arrayBuffer = await fileContent.arrayBuffer();
            
            // Convert ArrayBuffer to base64
            const base64Content = arrayBufferToBase64(arrayBuffer);
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
            console.error(`Error processing file ${file.name}:`, fileError);
            setDiscoveryMessages(prev => [...prev, `Error processing ${file.name}`]);
          }
        }

         // Build file tree
         const fileTree = buildFileTree(fileList);
         console.log("File tree:", fileTree);
         setFiles(fileTree);
         
         // Call onConnect with the files
         onFolderConnect(fileTree);
    
      } catch (error) {
        console.error('Error processing directory:', error);
        setDiscoveryMessages(prev => [...prev, "Error processing directory"]);
        setIsDiscovering(true);
      }
    };
    
    // Helper function to convert ArrayBuffer to base64
    const arrayBufferToBase64 = (buffer: ArrayBuffer): string => {
      let binary = '';
      const bytes = new Uint8Array(buffer);
      for (let i = 0; i < bytes.byteLength; i++) {
        binary += String.fromCharCode(bytes[i]);
      }
      return btoa(binary);
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
        // @ts-ignore - showDirectoryPicker is not in TypeScript types yet
        const dirHandle = await window.showDirectoryPicker();
        const dirName = dirHandle.name;
        const fullPath = await getFullPath(dirHandle);
        await processDirectory(dirHandle, fullPath);
      } catch (err) {
        console.log("User cancelled folder selection");
        setIsConnecting(false);
        setIsDiscovering(false);
      }
    };

    const getFullPath = async (dirHandle: any): Promise<string> => {
      try {
        // Just return the directory name instead of trying to resolve the full path
        return dirHandle.name;
      } catch (error) {
        console.error('Error getting full path:', error);
        return dirHandle.name || 'workspace';
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