// File: src/renderer/components/ui/CreateFileDialog.tsx
import React, { useState } from 'react';
import { File, Folder, FileSpreadsheet, FileText, FileImage, FileCode } from 'lucide-react';

interface CreateFileDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (name: string, template?: string) => void;
  isDirectory: boolean;
  parentPath: string;
  fileType?: {
    label: string;
    extension: string;
    template: string;
  };
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
    icon: <FileSpreadsheet className="w-4 h-4 text-green-500" />,
    template: 'excel'
  },
  {
    id: 'powerpoint',
    label: 'PowerPoint Presentation',
    extension: '.pptx',
    icon: <FileText className="w-4 h-4 text-orange-500" />,
    template: 'powerpoint'
  },
  {
    id: 'word',
    label: 'Word Document',
    extension: '.docx',
    icon: <FileText className="w-4 h-4 text-blue-500" />,
    template: 'word'
  }
];

export const CreateFileDialog: React.FC<CreateFileDialogProps> = ({
  isOpen,
  onClose,
  onConfirm,
  isDirectory,
  parentPath,
  fileType
}) => {
  const [name, setName] = useState('');
  const [selectedTemplate, setSelectedTemplate] = useState<FileTemplate | null>(null);

  // Pre-select template based on fileType prop
  React.useEffect(() => {
    if (fileType && isOpen) {
      const matchingTemplate = FILE_TEMPLATES.find(t => 
        t.extension === fileType.extension && t.template === fileType.template
      );
      setSelectedTemplate(matchingTemplate || null);
    }
  }, [fileType, isOpen]);

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
      <div className="bg-[#1a1a1a] rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[80vh] overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-700">
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
              className="w-full px-3 py-2 bg-[#2a2a2a] border border-gray-600 rounded-md text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:border-transparent"
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
              <div className="grid grid-cols-2 gap-1.5 sm:gap-2 max-h-64 overflow-y-auto">
                {FILE_TEMPLATES.map((template) => (
                  <button
                    key={template.id}
                    onClick={() => setSelectedTemplate(template)}
                    className={`
                      flex items-center gap-2 p-2 rounded-lg border transition-colors
                      ${selectedTemplate?.id === template.id
                        ? 'bg-gray-600 border-gray-500 text-white'
                        : 'bg-[#2a2a2a] border-gray-600 text-gray-200 hover:bg-gray-700'
                      }
                    `}
                  >
                    {template.icon}
                    <div className="text-sm opacity-70">{template.extension}</div>
                  </button>
                ))}
              </div>
              {selectedTemplate && (
                <div className="mt-2 p-2 bg-[#2a2a2a] rounded text-xs text-gray-300">
                  Selected: {selectedTemplate.label} ({selectedTemplate.extension})
                </div>
              )}
            </div>
          )}
        </div>

        <div className="px-6 py-4 border-t border-gray-700 flex justify-end gap-3">
          <button
            onClick={handleClose}
            className="px-4 py-2 text-gray-300 hover:text-white transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleConfirm}
            disabled={!name.trim()}
            className="px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Create
          </button>
        </div>
      </div>
    </div>
  );
};

export default CreateFileDialog;
