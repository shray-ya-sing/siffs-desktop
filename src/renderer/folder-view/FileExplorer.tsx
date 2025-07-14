// File: src/renderer/components/workspace/FileExplorer.tsx
import { useState, useEffect } from 'react';
import { 
  Folder, 
  FolderOpen, 
  File, 
  FileText, 
  FileSpreadsheet, 
  FileArchive, 
  FileJson, 
  FileImage, 
  FileCode,
  ChevronDown,
  ChevronRight
} from 'lucide-react';
import { fileWatcherService, FileWatcherService, FileChangeEvent } from '../services/fileWatcherService';
import { fileProcessingService } from '../services/fileProcessingService';

export interface FileItem {
  name: string;
  path: string;
  isDirectory: boolean;
  children?: FileItem[];
  expanded?: boolean;
}

interface FileExplorerProps {
  files: FileItem[];
  onFileSelect?: (file: FileItem) => void;
  className?: string;
}

const getFileIcon = (fileName: string) => {
  const extension = fileName.split('.').pop()?.toLowerCase();
  
  switch(extension) {
    case 'xlsx':
    case 'xls':
    case 'csv':
      return <FileSpreadsheet className="w-4 h-4 text-green-500" />;
    case 'docx':
    case 'doc':
      return <FileText className="w-4 h-4 text-blue-500" />;
    case 'pptx':
    case 'ppt':
      return <FileText className="w-4 h-4 text-orange-500" />;
    case 'pdf':
      return <FileText className="w-4 h-4 text-red-500" />;
    case 'json':
      return <FileJson className="w-4 h-4 text-yellow-500" />;
    case 'jpg':
    case 'jpeg':
    case 'png':
    case 'gif':
      return <FileImage className="w-4 h-4 text-purple-500" />;
    case 'js':
    case 'jsx':
    case 'ts':
    case 'tsx':
    case 'py':
    case 'java':
    case 'c':
    case 'cpp':
    case 'cs':
    case 'go':
    case 'rb':
    case 'php':
    case 'swift':
    case 'kt':
      return <FileCode className="w-4 h-4 text-blue-400" />;
    case 'txt':
    case 'md':
      return <FileText className="w-4 h-4 text-gray-400" />;
    default:
      return <File className="w-4 h-4 text-gray-500" />;
  }
};


 
const FileItem = ({ 
  item, 
  level = 0, 
  onToggle, 
  onSelect 
}: { 
  item: FileItem; 
  level: number; 
  onToggle: (item: FileItem) => void;
  onSelect?: (item: FileItem) => void;
}) => {
  const isExpandable = item.isDirectory && (item.children?.length ?? 0) > 0;
  
  return (
    <div className="w-full">
      <div 
        className={`
          flex items-center py-1.5 px-3 rounded-md mx-2 my-0.5
          ${!item.isDirectory ? 'hover:bg-gray-700/40' : ''}
          transition-colors duration-150
          ${level > 0 ? 'ml-2' : ''}
        `}
        style={{ paddingLeft: `${level * 12 + 8}px` }}
        onClick={() => {
            if (item.isDirectory) {
              onToggle(item);
            } else if (onSelect) {
              onSelect(item);
            }
          }}
      >
        {item.isDirectory ? (
          <div className="flex items-center text-gray-300">
            {item.expanded ? (
              <ChevronDown className="w-3 h-3 mr-1.5 text-gray-400" />
            ) : (
              <ChevronRight className="w-3 h-3 mr-1.5 text-gray-400" />
            )}
            {item.expanded ? (
              <FolderOpen className="w-3 h-3 mr-2 text-amber-400/80" />
            ) : (
              <Folder className="w-3 h-3 mr-2 text-amber-400/80" />
            )}
          </div>
        ) : (
          <div className="w-6 flex justify-center">
            {getFileIcon(item.name)}
          </div>
        )}
        <span className="text-xs text-gray-200 truncate">{item.name}</span>
      </div>
      
      {item.expanded && item.children && (
        <div className="w-full">
          {item.children.map((child) => (
            <FileItem
              key={child.path}
              item={child}
              level={level + 1}
              onToggle={onToggle}
              onSelect={onSelect}
            />
          ))}
        </div>
      )}
    </div>
  );
};

export const FileExplorer = ({ 
  files, 
  onFileSelect,
  className = ''
}: FileExplorerProps) => {
  const [fileTree, setFileTree] = useState<FileItem[]>(() => 
    files.map(file => ({ ...file, expanded: false }))
  );
  const [watcherPath, setWatcherPath] = useState<string | null>(null);

  // Set up file watcher when files change
  useEffect(() => {
    const handleFileChange = (event: FileChangeEvent) => {
      console.log('File change detected in FileExplorer:', event);
      
      // Forward all file change events to the file processing service
      // This handles cache invalidation and automatic backend processing
      fileProcessingService.handleFileChange(event);
      
      // Add new files/directories to the tree
      if (event.type === 'add' || event.type === 'addDir') {
        const newItem: FileItem = {
          name: event.relativePath.split('/').pop() || '',
          path: event.relativePath,
          isDirectory: event.type === 'addDir',
          expanded: false
        };
        
        setFileTree(currentTree => {
          // Check if item already exists to prevent duplicates
          const exists = findFileInTree(currentTree, newItem.path);
          if (exists) return currentTree;
          
          return addFileToTree(currentTree, newItem);
        });
      }
      
      // Remove files/directories from the tree
      if (event.type === 'unlink' || event.type === 'unlinkDir') {
        setFileTree(currentTree => removeFileFromTree(currentTree, event.relativePath));
      }
      
      // For file changes, the file processing service handles metadata refresh
      if (event.type === 'change' && FileWatcherService.shouldProcessFile(event.relativePath)) {
        console.log('Supported file changed, automatic processing queued:', event.relativePath);
      }
    };

    const unsubscribe = fileWatcherService.onFileChange(handleFileChange);
    return () => unsubscribe();
  }, []);

  const toggleExpand = (item: FileItem) => {
    const updateItem = (items: FileItem[]): FileItem[] => {
      return items.map(i => {
        if (i.path === item.path) {
          return { ...i, expanded: !i.expanded };
        }
        if (i.children) {
          return { ...i, children: updateItem(i.children) };
        }
        return i;
      });
    };

    setFileTree(updateItem(fileTree));
  };

  const handleFileSelect = (file: FileItem) => {
    if (onFileSelect && !file.isDirectory) {
      onFileSelect(file);
    }
  };

  // Helper function to find a file in the tree
  const findFileInTree = (tree: FileItem[], path: string): FileItem | null => {
    for (const item of tree) {
      if (item.path === path) {
        return item;
      }
      if (item.children) {
        const found = findFileInTree(item.children, path);
        if (found) return found;
      }
    }
    return null;
  };

  // Helper function to add a file to the tree
  const addFileToTree = (tree: FileItem[], newItem: FileItem): FileItem[] => {
    const pathParts = newItem.path.split('/');
    
    // If it's a root level item
    if (pathParts.length === 1) {
      return [...tree, newItem];
    }
    
    // Find the parent directory
    const parentPath = pathParts.slice(0, -1).join('/');
    
    return tree.map(item => {
      if (item.path === parentPath && item.isDirectory) {
        return {
          ...item,
          children: [...(item.children || []), newItem]
        };
      }
      
      if (item.children) {
        return {
          ...item,
          children: addFileToTree(item.children, newItem)
        };
      }
      
      return item;
    });
  };

  // Helper function to remove a file from the tree
  const removeFileFromTree = (tree: FileItem[], path: string): FileItem[] => {
    return tree.filter(item => {
      if (item.path === path) {
        return false; // Remove this item
      }
      
      if (item.children) {
        return {
          ...item,
          children: removeFileFromTree(item.children, path)
        };
      }
      
      return true;
    }).map(item => {
      if (item.children) {
        return {
          ...item,
          children: removeFileFromTree(item.children, path)
        };
      }
      return item;
    });
  };

  console.log("Rendering File tree:", fileTree);

  return (
    <div className={`h-full overflow-y-auto bg-transparent ${className}`}>
      <div className="py-2">
        {fileTree.length === 0 ? (
          <div className="text-center py-4 text-gray-500 text-sm">
            No files found
          </div>
        ) : (
          fileTree.map((item) => (
            <FileItem
              key={item.path}
              item={item}
              level={0}
              onToggle={toggleExpand}
              onSelect={onFileSelect}
            />
          ))
        )}
      </div>
    </div>
  );
};

export default FileExplorer;