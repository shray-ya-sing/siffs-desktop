// File: src/hooks/useFileTree.ts
import { useState, useCallback } from 'react';

export interface FileItem {
  name: string;
  path: string;
  isDirectory: boolean;
  children?: FileItem[];
  expanded?: boolean;
}

export const useFileTree = (initialFiles: FileItem[] = []) => {
  const [fileTree, setFileTree] = useState<FileItem[]>(() => 
    initialFiles.map(file => ({ ...file, expanded: false }))
  );

  const updateItem = useCallback((items: FileItem[], path: string, updates: Partial<FileItem>): FileItem[] => {
    return items.map(item => {
      if (item.path === path) {
        return { ...item, ...updates };
      }
      if (item.children) {
        return { 
          ...item, 
          children: updateItem(item.children, path, updates) 
        };
      }
      return item;
    });
  }, []);

  const toggleExpand = useCallback((path: string) => {
    setFileTree(prev => {
      const item = findItem(prev, path);
      if (item) {
        return updateItem(prev, path, { expanded: !item.expanded });
      }
      return prev;
    });
  }, [updateItem]);

  const findItem = useCallback((items: FileItem[], path: string): FileItem | null => {
    for (const item of items) {
      if (item.path === path) return item;
      if (item.children) {
        const found = findItem(item.children, path);
        if (found) return found;
      }
    }
    return null;
  }, []);

  const addFiles = useCallback((newFiles: FileItem[]) => {
    setFileTree(prev => [...prev, ...newFiles.map(f => ({ ...f, expanded: false }))]);
  }, []);

  return {
    fileTree,
    toggleExpand,
    addFiles,
    updateItem: (path: string, updates: Partial<FileItem>) => 
      setFileTree(prev => updateItem(prev, path, updates)),
  };
};