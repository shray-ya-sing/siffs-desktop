import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';

interface FileDiscoveryProgressProps {
  messages: string[];
  isActive: boolean;
}

export default function FileDiscoveryProgress({ messages, isActive }: FileDiscoveryProgressProps) {
  const [displayedMessage, setDisplayedMessage] = useState('');

  // Update the displayed message when messages array changes
  useEffect(() => {
    if (messages.length > 0) {
      setDisplayedMessage(messages[messages.length - 1]);
    }
  }, [messages]);

  if (!isActive || !displayedMessage) return null;

  return (
    <div className="fixed bottom-8 left-1/2 transform -translate-x-1/2 z-50 max-w-md w-full px-4">
      <div 
        className="relative p-4 overflow-hidden"
        style={{
          background: 'linear-gradient(135deg, rgba(42, 42, 42, 0.8) 0%, rgba(26, 26, 26, 0.8) 100%)',
          border: '1px solid rgba(51, 51, 51, 0.5)',
          borderRadius: '1.5rem',
          backdropFilter: 'blur(8px)'
        }}
      >
        {/* Animated gradient border */}
        <motion.div
          className="absolute inset-0 rounded-3xl p-[1px]"
          style={{
            background: 'linear-gradient(135deg, rgba(59, 130, 246, 0.5) 0%, rgba(14, 165, 233, 0.5) 100%)',
            WebkitMask: 'linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0)',
            WebkitMaskComposite: 'xor',
            maskComposite: 'exclude',
            pointerEvents: 'none'
          }}
          initial={{ opacity: 0.7 }}
          animate={{ 
            opacity: [0.7, 1, 0.7],
            transition: {
              duration: 3,
              repeat: Infinity,
              repeatType: 'loop',
              ease: 'easeInOut'
            }
          }}
        />
        
        {/* Message content */}
        <div className="flex items-center space-x-3">
          <div className="flex-shrink-0">
            <div className="w-2 h-2 rounded-full bg-blue-400 animate-pulse" />
          </div>
          <p 
            className="text-sm text-gray-200 truncate" 
            style={{ textShadow: '0 1px 2px rgba(0,0,0,0.5)' }}
            title={displayedMessage}
          >
            {displayedMessage}
          </p>
        </div>
      </div>
    </div>
  );
}