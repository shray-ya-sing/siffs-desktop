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