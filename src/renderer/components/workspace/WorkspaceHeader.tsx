import React, { useState, useRef, useEffect } from 'react';
import { FolderPlus, FilePlus, ChevronDown } from 'lucide-react';
import { TechExcelIcon, TechWordIcon, TechPowerPointIcon } from '../tech-icons/TechIcons';
import { fileProcessingService } from '../../services/fileProcessingService';
import CreateFileDialog from '../ui/CreateFileDialog';

interface WorkspaceHeaderProps {
  onToggleSidebar: () => void;
  itemCount: number;
}

interface FileTypeOption {
  label: string;
  extension: string;
  icon: React.ReactNode;
  template: string;
}

const fileTypeOptions: FileTypeOption[] = [
  {
    label: 'Excel Spreadsheet',
    extension: '.xlsx',
    icon: <TechExcelIcon className="w-4 h-4" />,
    template: 'excel'
  },
  {
    label: 'PowerPoint Presentation',
    extension: '.pptx',
    icon: <TechPowerPointIcon className="w-4 h-4" />,
    template: 'powerpoint'
  },
  {
    label: 'Word Document',
    extension: '.docx',
    icon: <TechWordIcon className="w-4 h-4" />,
    template: 'word'
  }
];

export const WorkspaceHeader: React.FC<WorkspaceHeaderProps> = ({ onToggleSidebar, itemCount }) => {
  const [showFileDropdown, setShowFileDropdown] = useState(false);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [createDialogIsDirectory, setCreateDialogIsDirectory] = useState(false);
  const [selectedFileType, setSelectedFileType] = useState<FileTypeOption | null>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setShowFileDropdown(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const getWorkspacePath = (): string | null => {
    const processingContext = (fileProcessingService as any).processingContext;
    return processingContext?.workspacePath || null;
  };

  const handleCreateFolder = () => {
    const workspacePath = getWorkspacePath();
    if (!workspacePath) {
      alert('No workspace connected. Please connect a folder first.');
      return;
    }

    setCreateDialogIsDirectory(true);
    setSelectedFileType(null);
    setShowCreateDialog(true);
  };

  const handleCreateFile = (fileType: FileTypeOption) => {
    const workspacePath = getWorkspacePath();
    if (!workspacePath) {
      alert('No workspace connected. Please connect a folder first.');
      return;
    }

    setCreateDialogIsDirectory(false);
    setSelectedFileType(fileType);
    setShowCreateDialog(true);
    setShowFileDropdown(false);
  };

  const handleConfirmCreate = async (name: string, template?: string) => {
    const workspacePath = getWorkspacePath();
    if (!workspacePath) return;

    try {
      const electron = (window as any).electron;
      
      if (createDialogIsDirectory) {
        const result = await electron.fileSystem.createDirectory(workspacePath, name);
        if (result.success) {
          console.log('Folder created successfully:', result.folderPath);
        } else {
          console.error('Failed to create folder:', result.error);
          alert('Failed to create folder: ' + result.error);
        }
      } else if (selectedFileType) {
        const fullFileName = name.endsWith(selectedFileType.extension) 
          ? name 
          : name + selectedFileType.extension;
          
        const result = await electron.fileSystem.createFile(workspacePath, fullFileName, selectedFileType.template);
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
    <>
      <div className="flex items-center justify-between p-3 border-b border-gray-700/50">
        <h2 className="text-base font-medium text-gray-200">Workspace</h2>
        
        <div className="flex items-center gap-2">
          {/* Folder creation button */}
          <button
            onClick={handleCreateFolder}
            className="p-1.5 rounded-md hover:bg-gray-700/50 text-gray-400 hover:text-gray-200 transition-colors"
            title="Create new folder"
          >
            <FolderPlus className="w-4 h-4" />
          </button>

          {/* File creation dropdown */}
          <div className="relative" ref={dropdownRef}>
            <button
              onClick={() => setShowFileDropdown(!showFileDropdown)}
              className="flex items-center gap-1 p-1.5 rounded-md hover:bg-gray-700/50 text-gray-400 hover:text-gray-200 transition-colors"
              title="Create new file"
            >
              <FilePlus className="w-4 h-4" />
              <ChevronDown className="w-3 h-3" />
            </button>

            {showFileDropdown && (
              <div className="absolute right-0 top-full mt-1 bg-[#1a1a1a] border border-gray-700 rounded-md shadow-lg py-1 z-50 min-w-[200px]">
                {fileTypeOptions.map((option) => (
                  <button
                    key={option.extension}
                    onClick={() => handleCreateFile(option)}
                    className="w-full flex items-center gap-3 px-3 py-2 text-sm text-gray-200 hover:bg-gray-800 transition-colors text-left"
                  >
                    {option.icon}
                    <span>{option.label}</span>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Sidebar toggle button */}
          <button
            onClick={onToggleSidebar}
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
      </div>

      {/* Create File/Folder Dialog */}
      <CreateFileDialog
        isOpen={showCreateDialog}
        onClose={() => setShowCreateDialog(false)}
        onConfirm={handleConfirmCreate}
        isDirectory={createDialogIsDirectory}
        parentPath={getWorkspacePath() || ''}
        fileType={selectedFileType ? {
          label: selectedFileType.label,
          extension: selectedFileType.extension,
          template: selectedFileType.template
        } : undefined}
      />
    </>
  );
};

export default WorkspaceHeader;
