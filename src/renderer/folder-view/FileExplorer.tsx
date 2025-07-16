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
import { TechExcelIcon, TechWordIcon, TechPowerPointIcon, TechPDFIcon } from '../components/tech-icons/TechIcons';
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
      return <TechExcelIcon className="w-4 h-4" />;
    case 'docx':
    case 'doc':
      return <TechWordIcon className="w-4 h-4" />;
    case 'pptx':
    case 'ppt':
      return <TechPowerPointIcon className="w-4 h-4" />;
    case 'pdf':
      return <TechPDFIcon className="w-4 h-4" />;
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
  showContextMenu,
  onDragStart,
  onDragOver,
  onDrop,
  draggedItem,
  dragOverItem
}: { 
  item: FileItem; 
  level: number; 
  showContextMenu: (event: React.MouseEvent, item: FileItem) => void;
  onToggle: (item: FileItem) => void;
  onSelect?: (item: FileItem) => void;
  onDragStart?: (item: FileItem) => void;
  onDragOver?: (event: React.DragEvent, item: FileItem) => void;
  onDrop?: (event: React.DragEvent, item: FileItem) => void;
  draggedItem?: FileItem | null;
  dragOverItem?: FileItem | null;
}) => {
  const isExpandable = item.isDirectory && (item.children?.length ?? 0) > 0;
  
  return (
    <div className="w-full">
      <div 
        className={`
          flex items-center py-1.5 px-3 rounded-md mx-2 my-0.5
          ${!item.isDirectory ? 'hover:bg-gray-700/40' : ''}
          ${draggedItem?.path === item.path ? 'opacity-50' : ''}
          ${dragOverItem?.path === item.path && item.isDirectory ? 'bg-blue-600/30 border border-blue-500' : ''}
          transition-colors duration-150
          ${level > 0 ? 'ml-2' : ''}
          cursor-pointer
        `}
        style={{ paddingLeft: `${level * 12 + 8}px` }}
        draggable={true}
        onDragStart={(e) => {
          e.stopPropagation();
          if (onDragStart) {
            onDragStart(item);
          }
        }}
        onDragOver={(e) => {
          e.preventDefault();
          e.stopPropagation();
          if (onDragOver && item.isDirectory) {
            onDragOver(e, item);
          }
        }}
        onDragLeave={(e) => {
          e.stopPropagation();
          // Only clear drag over if we're leaving the actual item
          const rect = e.currentTarget.getBoundingClientRect();
          const x = e.clientX;
          const y = e.clientY;
          
          if (x < rect.left || x > rect.right || y < rect.top || y > rect.bottom) {
            if (onDragOver) {
              onDragOver(e, null as any);
            }
          }
        }}
        onDrop={(e) => {
          e.preventDefault();
          e.stopPropagation();
          if (onDrop && item.isDirectory) {
            onDrop(e, item);
          }
        }}
        onClick={() => {
            if (item.isDirectory) {
              onToggle(item);
            } else if (onSelect) {
              onSelect(item);
            }
          }}
        onContextMenu={(event) => {
          event.preventDefault();
          event.stopPropagation(); // Prevent workspace context menu from showing
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
              onDragStart={onDragStart}
              onDragOver={onDragOver}
              onDrop={onDrop}
              draggedItem={draggedItem}
              dragOverItem={dragOverItem}
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
  const [copiedFile, setCopiedFile] = useState<{ path: string; name: string; isDirectory: boolean } | null>(null);
  const [draggedItem, setDraggedItem] = useState<FileItem | null>(null);
  const [dragOverItem, setDragOverItem] = useState<FileItem | null>(null);

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
        action: () => electron.fileSystem.revealInExplorer(absolutePath)
      },
      { label: 'Cut', action: () => {/* implementation */}, disabled: true },
      { 
        label: 'Copy', 
        action: () => {
          // Copy any file or folder
          setCopiedFile({ path: item.path, name: item.name, isDirectory: item.isDirectory });
          console.log('📋 Copied:', item.isDirectory ? 'folder' : 'file', item.name);
        }
      },
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
      },
      {
        label: 'Paste',
        action: async () => {
          if (copiedFile) {
            try {
              const sourceAbsolutePath = resolveToAbsolutePath(copiedFile.path);
              
              // Generate destination filename with "copy" suffix
              const originalName = copiedFile.name;
              const lastDotIndex = originalName.lastIndexOf('.');
              let destinationFileName;
              
              if (lastDotIndex === -1) {
                // No extension
                destinationFileName = originalName + ' copy';
              } else {
                // Has extension
                const nameWithoutExt = originalName.substring(0, lastDotIndex);
                const extension = originalName.substring(lastDotIndex);
                destinationFileName = nameWithoutExt + ' copy' + extension;
              }
              
              const destinationAbsolutePath = absolutePath + (navigator.platform.toLowerCase().includes('win') ? '\\' : '/') + destinationFileName;
              
              console.log('📋 Pasting file:', {
                source: sourceAbsolutePath,
                destination: destinationAbsolutePath,
                originalName,
                newName: destinationFileName
              });
              
              // Debug: Check if copyFile function exists
              console.log('🔍 Checking electron.fileSystem.copyFile:', typeof electron.fileSystem.copyFile);
              
              const result = await electron.fileSystem.copyFile(sourceAbsolutePath, destinationAbsolutePath);
              if (result.success) {
                console.log('✅ File pasted successfully:', result.destinationPath);
                // Clear the copied file after successful paste
                setCopiedFile(null);
              } else {
                console.error('❌ Failed to paste file:', result.error);
                alert('Failed to paste file: ' + result.error);
              }
            } catch (error) {
              console.error('❌ Error pasting file:', error);
              alert('An error occurred while pasting the file');
            }
          }
        },
        disabled: !copiedFile
      }
    ];

    const fileSpecificItems: ContextMenuItem[] = [
      {
        label: 'Open',
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

  // Drag and drop handlers
  const handleDragStart = (item: FileItem) => {
    console.log('🚚 Drag started for:', item.name);
    setDraggedItem(item);
  };

  const handleDragOver = (event: React.DragEvent, targetItem: FileItem | null) => {
    if (targetItem && targetItem.isDirectory) {
      setDragOverItem(targetItem);
    } else {
      setDragOverItem(null);
    }
  };

  const handleDrop = async (event: React.DragEvent, targetItem: FileItem) => {
    console.log('📁 Drop detected:', { draggedItem, targetItem });
    
    if (!draggedItem || !targetItem.isDirectory || draggedItem.path === targetItem.path) {
      setDraggedItem(null);
      setDragOverItem(null);
      return;
    }

    // Prevent dropping a folder into itself or its children
    if (draggedItem.isDirectory && targetItem.path.startsWith(draggedItem.path)) {
      console.warn('Cannot move folder into itself or its children');
      alert('Cannot move a folder into itself or its children');
      setDraggedItem(null);
      setDragOverItem(null);
      return;
    }

    try {
      const electron = (window as any).electron;
      const sourceAbsolutePath = resolveToAbsolutePath(draggedItem.path);
      const targetAbsolutePath = resolveToAbsolutePath(targetItem.path);
      const destinationPath = targetAbsolutePath + (navigator.platform.toLowerCase().includes('win') ? '\\' : '/') + draggedItem.name;
      
      console.log('🚚 Moving file/folder:', {
        source: sourceAbsolutePath,
        destination: destinationPath
      });
      
      const result = await electron.fileSystem.moveFile(sourceAbsolutePath, destinationPath);
      
      if (result.success) {
        console.log('✅ File/folder moved successfully:', result.destinationPath);
      } else {
        console.error('❌ Failed to move file/folder:', result.error);
        alert('Failed to move file/folder: ' + result.error);
      }
    } catch (error) {
      console.error('❌ Error moving file/folder:', error);
      alert('An error occurred while moving the file/folder');
    }
    
    setDraggedItem(null);
    setDragOverItem(null);
  };

  const showWorkspaceContextMenu = (event: React.MouseEvent) => {
    // Only show workspace context menu if the target is the container itself or the py-2 div
    const target = event.target as HTMLElement;
    const isWorkspaceContainer = target.classList.contains('h-full') || 
                                target.classList.contains('py-2') ||
                                target.tagName === 'DIV' && !target.closest('[data-file-item]');
    
    if (!isWorkspaceContainer) {
      return; // Don't show workspace context menu if clicking on file items
    }

    console.log('🖱️ Workspace context menu triggered at position:', { x: event.clientX, y: event.clientY });
    event.preventDefault();
    setContextMenuPosition({ x: event.clientX, y: event.clientY });

    const electron = (window as any).electron;
    const processingContext = (fileProcessingService as any).processingContext;
    
    const workspaceRootItems: ContextMenuItem[] = [
      {
        label: 'Paste',
        action: async () => {
          if (copiedFile && processingContext && processingContext.workspacePath) {
            try {
              const sourceAbsolutePath = resolveToAbsolutePath(copiedFile.path);
              
              // Generate destination filename with "copy" suffix
              const originalName = copiedFile.name;
              const lastDotIndex = originalName.lastIndexOf('.');
              let destinationFileName;
              
              if (lastDotIndex === -1) {
                // No extension
                destinationFileName = originalName + ' copy';
              } else {
                // Has extension
                const nameWithoutExt = originalName.substring(0, lastDotIndex);
                const extension = originalName.substring(lastDotIndex);
                destinationFileName = nameWithoutExt + ' copy' + extension;
              }
              
              const destinationAbsolutePath = processingContext.workspacePath + (navigator.platform.toLowerCase().includes('win') ? '\\' : '/') + destinationFileName;
              
              console.log('📋 Pasting file to workspace root:', {
                source: sourceAbsolutePath,
                destination: destinationAbsolutePath,
                originalName,
                newName: destinationFileName
              });
              
              // Debug: Check if copyFile function exists
              console.log('🔍 Checking electron.fileSystem.copyFile:', typeof electron.fileSystem.copyFile);
              
              const result = await electron.fileSystem.copyFile(sourceAbsolutePath, destinationAbsolutePath);
              if (result.success) {
                console.log('✅ File pasted to workspace root successfully:', result.destinationPath);
                // Clear the copied file after successful paste
                setCopiedFile(null);
              } else {
                console.error('❌ Failed to paste file to workspace root:', result.error);
                alert('Failed to paste file: ' + result.error);
              }
            } catch (error) {
              console.error('❌ Error pasting file to workspace root:', error);
              alert('An error occurred while pasting the file');
            }
          }
        },
        disabled: !copiedFile
      }
    ];

    setContextMenuItems(workspaceRootItems);
  };

  return (
    <div 
      className={`h-full overflow-y-auto bg-transparent ${className}`}
      onContextMenu={showWorkspaceContextMenu}
    >
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
                onDragStart={handleDragStart}
                onDragOver={handleDragOver}
                onDrop={handleDrop}
                draggedItem={draggedItem}
                dragOverItem={dragOverItem}
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