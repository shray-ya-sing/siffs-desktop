/*
 * Siffs - Fast File Search Desktop Application
 * Copyright (C) 2025  Siffs
 * 
 * Contact: github.suggest277@passinbox.com
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */
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
    console.log('addFiles called with:', newFiles);
    setFileTree(prev => {
      console.log('Previous fileTree:', prev);
      const newTree = [...prev, ...newFiles.map(f => ({ ...f, expanded: false }))];
      console.log('New fileTree:', newTree);
      return newTree;
    });
  }, []);

  return {
    fileTree,
    toggleExpand,
    addFiles,
    updateItem: (path: string, updates: Partial<FileItem>) => 
      setFileTree(prev => updateItem(prev, path, updates)),
  };
};