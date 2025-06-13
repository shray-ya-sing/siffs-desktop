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