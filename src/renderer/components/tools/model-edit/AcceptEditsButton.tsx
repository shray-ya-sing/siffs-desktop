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
import React from 'react';
import { Button } from '../../ui/button';

interface AcceptEditsButtonProps {
  onAccept: () => Promise<void>;
  pendingCount: number;
  disabled?: boolean;
  className?: string;
}

export const AcceptEditsButton: React.FC<AcceptEditsButtonProps> = ({
  onAccept,
  pendingCount,
  disabled = false,
  className = ''
}) => {
  const [isProcessing, setIsProcessing] = React.useState(false);

  const handleAccept = async () => {
    if (pendingCount === 0) return;
    
    try {
      setIsProcessing(true);
      await onAccept();
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <Button
      onClick={handleAccept}
      disabled={disabled || pendingCount === 0 || isProcessing}
      variant="default"
      className={className}
    >
      {isProcessing ? (
        'Accepting...'
      ) : (
        `Accept Edits${pendingCount > 0 ? ` (${pendingCount})` : ''}`
      )}
    </Button>
  );
};