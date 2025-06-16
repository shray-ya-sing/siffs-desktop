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
      <div className="relative bg-gray-900/90 backdrop-blur-sm rounded-xl p-4 border border-gray-700/50 overflow-hidden">
        {/* Animated gradient border bottom */}
        <motion.div
          className="absolute bottom-0 left-0 h-0.5 bg-gradient-to-r from-blue-500 via-blue-400 to-cyan-400"
          initial={{ width: '0%' }}
          animate={{ 
            width: '100%',
            transition: {
              duration: 2,
              repeat: Infinity,
              repeatType: 'loop',
              ease: 'linear'
            }
          }}
        />
        
        {/* Shimmer effect */}
        <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
        
        {/* Message content */}
        <div className="flex items-center space-x-3">
          <div className="flex-shrink-0">
            <div className="w-2 h-2 rounded-full bg-blue-400 animate-pulse" />
          </div>
          <p className="text-sm text-gray-200 truncate" title={displayedMessage}>
            {displayedMessage}
          </p>
        </div>
      </div>
    </div>
  );
}