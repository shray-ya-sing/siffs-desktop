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
  ChevronRight,
  ExternalLink,
  Copy,
  Scissors,
  Edit,
  Trash2,
  FolderPlus,
  FilePlus
} from 'lucide-react';
import { fileWatcherService, FileWatcherService, FileChangeEvent } from '../services/fileWatcherService';
import { fileProcessingService } from '../services/fileProcessingService';

import ContextMenu, { ContextMenuItem } from '../components/ui/ContextMenu';
import CreateFileDialog from '../components/ui/CreateFileDialog';
import RenameDialog from '../components/ui/RenameDialog';

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


 
const FileTreeItem = ({ 
  item, 
  level = 0, 
  onToggle, 
  onSelect,
  showContextMenu
}: { 
  item: FileItem; 
  level: number; 
  showContextMenu: (event: React.MouseEvent, item: FileItem) => void;
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
        onContextMenu={(event) => {
          event.preventDefault();
          showContextMenu(event, item);
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
            <FileTreeItem
              key={child.path}
              item={child}
              level={level + 1}
              onToggle={onToggle}
              onSelect={onSelect}
              showContextMenu={showContextMenu}
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

  const [contextMenuPosition, setContextMenuPosition] = useState<{ x: number; y: number } | null>(null);
  const [contextMenuItems, setContextMenuItems] = useState<ContextMenuItem[]>([]);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [createDialogIsDirectory, setCreateDialogIsDirectory] = useState(false);
  const [createDialogParentPath, setCreateDialogParentPath] = useState('');
  const [renameDialogOpen, setRenameDialogOpen] = useState(false);  
  const [renameItem, setRenameItem] = useState<{ path: string; name: string; isDirectory: boolean } | null>(null);

  // Helper function to resolve relative path to absolute path
  const resolveToAbsolutePath = (relativePath: string): string => {
    const processingContext = (fileProcessingService as any).processingContext;
    if (processingContext && processingContext.workspacePath) {
      // Normalize the relative path to use forward slashes for joining
      const normalizedRelativePath = relativePath.replace(/\\/g, '/');
      const fullPath = `${processingContext.workspacePath}/${normalizedRelativePath}`;
      
      // On Windows, convert all path separators to backslashes
      if (navigator.platform.toLowerCase().includes('win')) {
        return fullPath.replace(/\//g, '\\');
      }
      
      // On other platforms, use forward slashes
      return fullPath.replace(/\/+/g, '/');
    }
    // Fallback to relative path if no workspace context
    return relativePath;
  };

  const showContextMenu = (event: React.MouseEvent, item: FileItem) => {
    console.log('🖱️ Context menu triggered for item:', item.name, 'at position:', { x: event.clientX, y: event.clientY });
    setContextMenuPosition({ x: event.clientX, y: event.clientY });

    // Type assertion to ensure TypeScript recognizes the full electron API
    const electron = (window as any).electron;

    // Resolve item path to absolute path for file operations
    const absolutePath = resolveToAbsolutePath(item.path);

    const commonItems: ContextMenuItem[] = [
      {
        label: 'Reveal in File Explorer',
        action: () => electron.fileSystem.revealInExplorer(absolutePath),
        disabled: item.isDirectory
      },
      { label: 'Cut', action: () => {/* implementation */}, disabled: true },
      { label: 'Copy', action: () => electron.fileSystem.copyToClipboard(absolutePath) },
      { label: 'Copy Path', action: () => electron.fileSystem.copyToClipboard(absolutePath) },
      {
        label: 'Rename',
        action: () => {
          setRenameItem({ path: absolutePath, name: item.name, isDirectory: item.isDirectory });
          setRenameDialogOpen(true);
        }
      },
      {
        label: 'Delete',
        action: async () => {
          const confirmed = confirm(`Are you sure you want to delete ${item.name}?`);
          if (confirmed) {
            if (item.isDirectory) {
              await electron.fileSystem.deleteDirectory(absolutePath);
            } else {
              await electron.fileSystem.deleteFile(absolutePath);
            }
          }
        },
        destructive: true
      }
    ];

    const folderSpecificItems: ContextMenuItem[] = [
      {
        label: 'New File...',
        action: () => {
          setCreateDialogIsDirectory(false);
          setCreateDialogParentPath(absolutePath);
          setShowCreateDialog(true);
        }
      },
      {
        label: 'New Folder...',
        action: () => {
          setCreateDialogIsDirectory(true);
          setCreateDialogParentPath(absolutePath);
          setShowCreateDialog(true);
        }
      }
    ];

    const fileSpecificItems: ContextMenuItem[] = [
      {
        label: 'Open With...',
        action: () => electron.fileSystem.openWithDefault(absolutePath),
        disabled: item.isDirectory
      }
    ];

    const items = item.isDirectory ? [...folderSpecificItems, ...commonItems] : [...fileSpecificItems, ...commonItems];
    setContextMenuItems(items);
  };

  const handleCloseContextMenu = () => {
    setContextMenuPosition(null);
    setContextMenuItems([]);
  };

  const handleCreateFile = async (name: string, template?: string) => {
    try {
      // Type assertion to ensure TypeScript recognizes the full electron API
      const electron = (window as any).electron;
      
      if (createDialogIsDirectory) {
        const result = await electron.fileSystem.createDirectory(createDialogParentPath, name);
        if (result.success) {
          console.log('Folder created successfully:', result.folderPath);
        } else {
          console.error('Failed to create folder:', result.error);
          alert('Failed to create folder: ' + result.error);
        }
      } else {
        const result = await electron.fileSystem.createFile(createDialogParentPath, name, template);
        if (result.success) {
          console.log('File created successfully:', result.filePath);
        } else {
          console.error('Failed to create file:', result.error);
          alert('Failed to create file: ' + result.error);
        }
      }
    } catch (error) {
      console.error('Error creating file/folder:', error);
      alert('An error occurred while creating the ' + (createDialogIsDirectory ? 'folder' : 'file'));
    }
    setShowCreateDialog(false);
  };

  return (
    <div className={`h-full overflow-y-auto bg-transparent ${className}`}>
      <div className="py-2">
        {fileTree.length === 0 ? (
          <div className="text-center py-4 text-gray-500 text-sm">
            No files found
          </div>
        ) : (
          <>
            <ContextMenu items={contextMenuItems} position={contextMenuPosition} onClose={handleCloseContextMenu} />
            {fileTree.map((item) => (
              <FileTreeItem
                showContextMenu={showContextMenu}
                key={item.path}
                item={item}
                level={0}
                onToggle={toggleExpand}
                onSelect={onFileSelect}
              />
            ))}
          </>
        )}
      </div>
      
      <CreateFileDialog
        isOpen={showCreateDialog}
        onClose={() => setShowCreateDialog(false)}
        onConfirm={handleCreateFile}
        isDirectory={createDialogIsDirectory}
        parentPath={createDialogParentPath}
      />

      <RenameDialog
        isOpen={renameDialogOpen}
        onClose={() => setRenameDialogOpen(false)}
        onConfirm={async (newName) => {
          if (renameItem) {
            try {
              const result = await (window as any).electron.fileSystem.renameFile(renameItem.path, newName);
              if (result.success) {
                console.log('File renamed successfully:', result.newPath);
              } else {
                console.error('Failed to rename file:', result.error);
                alert('Failed to rename file: ' + result.error);
              }
            } catch (error) {
              console.error('Error renaming file:', error);
              alert('An error occurred while renaming the file/folder');
            }
          }
        }}
        currentName={renameItem?.name || ''}
        isDirectory={renameItem?.isDirectory || false}
      />
    </div>
  );
};

export default FileExplorer;