// File: src/renderer/components/ui/CreateFileDialog.tsx
import React, { useState } from 'react';
import { File, Folder, FileSpreadsheet, FileText, FileImage, FileCode } from 'lucide-react';

interface CreateFileDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (name: string, template?: string) => void;
  isDirectory: boolean;
  parentPath: string;
}

interface FileTemplate {
  id: string;
  label: string;
  extension: string;
  icon: React.ReactNode;
  template: string;
}

const FILE_TEMPLATES: FileTemplate[] = [
  {
    id: 'excel',
    label: 'Excel Workbook',
    extension: '.xlsx',
    icon: <FileSpreadsheet className="w-5 h-5 text-green-500" />,
    template: 'excel'
  },
  {
    id: 'powerpoint',
    label: 'PowerPoint Presentation',
    extension: '.pptx',
    icon: <FileText className="w-5 h-5 text-orange-500" />,
    template: 'powerpoint'
  },
  {
    id: 'word',
    label: 'Word Document',
    extension: '.docx',
    icon: <FileText className="w-5 h-5 text-blue-500" />,
    template: 'word'
  },
  {
    id: 'text',
    label: 'Text File',
    extension: '.txt',
    icon: <FileText className="w-5 h-5 text-gray-400" />,
    template: 'text'
  },
  {
    id: 'markdown',
    label: 'Markdown File',
    extension: '.md',
    icon: <FileText className="w-5 h-5 text-gray-400" />,
    template: 'markdown'
  },
  {
    id: 'json',
    label: 'JSON File',
    extension: '.json',
    icon: <FileCode className="w-5 h-5 text-yellow-500" />,
    template: 'json'
  },
  {
    id: 'javascript',
    label: 'JavaScript File',
    extension: '.js',
    icon: <FileCode className="w-5 h-5 text-yellow-400" />,
    template: 'javascript'
  },
  {
    id: 'typescript',
    label: 'TypeScript File',
    extension: '.ts',
    icon: <FileCode className="w-5 h-5 text-blue-400" />,
    template: 'typescript'
  },
  {
    id: 'python',
    label: 'Python File',
    extension: '.py',
    icon: <FileCode className="w-5 h-5 text-blue-400" />,
    template: 'python'
  },
  {
    id: 'html',
    label: 'HTML File',
    extension: '.html',
    icon: <FileCode className="w-5 h-5 text-orange-400" />,
    template: 'html'
  },
  {
    id: 'css',
    label: 'CSS File',
    extension: '.css',
    icon: <FileCode className="w-5 h-5 text-blue-300" />,
    template: 'css'
  }
];

export const CreateFileDialog: React.FC<CreateFileDialogProps> = ({
  isOpen,
  onClose,
  onConfirm,
  isDirectory,
  parentPath
}) => {
  const [name, setName] = useState('');
  const [selectedTemplate, setSelectedTemplate] = useState<FileTemplate | null>(null);

  const handleConfirm = () => {
    if (!name.trim()) return;

    let finalName = name.trim();
    
    if (!isDirectory && selectedTemplate) {
      // Add extension if not already present
      if (!finalName.toLowerCase().endsWith(selectedTemplate.extension)) {
        finalName += selectedTemplate.extension;
      }
      onConfirm(finalName, selectedTemplate.template);
    } else {
      onConfirm(finalName);
    }

    // Reset state
    setName('');
    setSelectedTemplate(null);
  };

  const handleClose = () => {
    setName('');
    setSelectedTemplate(null);
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[80vh] overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-600">
          <h2 className="text-xl font-semibold text-white">
            {isDirectory ? 'Create New Folder' : 'Create New File'}
          </h2>
          <p className="text-sm text-gray-400 mt-1">
            in {parentPath}
          </p>
        </div>

        <div className="p-6 space-y-4 overflow-y-auto max-h-96">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              {isDirectory ? 'Folder Name' : 'File Name'}
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder={isDirectory ? 'Enter folder name' : 'Enter file name'}
              autoFocus
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  handleConfirm();
                } else if (e.key === 'Escape') {
                  handleClose();
                }
              }}
            />
          </div>

          {!isDirectory && (
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-3">
                File Template (Optional)
              </label>
              <div className="grid grid-cols-2 gap-2 max-h-64 overflow-y-auto">
                {FILE_TEMPLATES.map((template) => (
                  <button
                    key={template.id}
                    onClick={() => setSelectedTemplate(template)}
                    className={`
                      flex items-center gap-3 p-3 rounded-lg border transition-colors
                      ${selectedTemplate?.id === template.id
                        ? 'bg-blue-600 border-blue-500 text-white'
                        : 'bg-gray-700 border-gray-600 text-gray-200 hover:bg-gray-600'
                      }
                    `}
                  >
                    {template.icon}
                    <div className="text-left">
                      <div className="text-sm font-medium">{template.label}</div>
                      <div className="text-xs opacity-70">{template.extension}</div>
                    </div>
                  </button>
                ))}
              </div>
              {selectedTemplate && (
                <div className="mt-2 p-2 bg-gray-700 rounded text-xs text-gray-300">
                  Selected: {selectedTemplate.label} ({selectedTemplate.extension})
                </div>
              )}
            </div>
          )}
        </div>

        <div className="px-6 py-4 border-t border-gray-600 flex justify-end gap-3">
          <button
            onClick={handleClose}
            className="px-4 py-2 text-gray-300 hover:text-white transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleConfirm}
            disabled={!name.trim()}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Create
          </button>
        </div>
      </div>
    </div>
  );
};

export default CreateFileDialog;
