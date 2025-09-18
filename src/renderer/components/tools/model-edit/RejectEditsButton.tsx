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
// src/renderer/components/tools/model-edit/RejectEditsButton.tsx
import React from 'react';
import { Button } from '../../ui/button';

interface RejectEditsButtonProps {
  onReject: () => Promise<void>;
  pendingCount: number;
  disabled?: boolean;
  className?: string;
}

export const RejectEditsButton: React.FC<RejectEditsButtonProps> = ({
  onReject,
  pendingCount,
  disabled = false,
  className = ''
}) => {
  const [isProcessing, setIsProcessing] = React.useState(false);

  const handleReject = async () => {
    if (pendingCount === 0) return;
    
    try {
      setIsProcessing(true);
      await onReject();
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <Button
      onClick={handleReject}
      disabled={disabled || pendingCount === 0 || isProcessing}
      variant="outline"  
      className={`border-red-500 text-red-500 hover:bg-red-50 hover:text-red-600 ${className}`}
    >
      {isProcessing ? (
        'Rejecting...'
      ) : (
        `Reject Edits${pendingCount > 0 ? ` (${pendingCount})` : ''}`
      )}
    </Button>
  );
};