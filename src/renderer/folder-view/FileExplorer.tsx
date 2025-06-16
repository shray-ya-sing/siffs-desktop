// File: src/renderer/components/workspace/FileExplorer.tsx
import { useState } from 'react';
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
              <ChevronDown className="w-4 h-4 mr-1.5 text-gray-400" />
            ) : (
              <ChevronRight className="w-4 h-4 mr-1.5 text-gray-400" />
            )}
            {item.expanded ? (
              <FolderOpen className="w-4 h-4 mr-2 text-amber-400/80" />
            ) : (
              <Folder className="w-4 h-4 mr-2 text-amber-400/80" />
            )}
          </div>
        ) : (
          <div className="w-6 flex justify-center">
            {getFileIcon(item.name)}
          </div>
        )}
        <span className="text-sm text-gray-200 truncate">{item.name}</span>
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