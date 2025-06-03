import React, { useEffect } from 'react';
import { motion } from 'framer-motion';

interface AuthLoadingProps {
  message?: string;
}

export default function AuthLoading({ message = 'Signing in...' }: AuthLoadingProps) {
    return (
        <div className="w-full p-6">
          <div className="max-w-xs mx-auto space-y-6 flex flex-col items-center">
            {/* Spinner and message */}
            {/* Spinner with gradient */}
            <div className="relative w-16 h-16">
                <div className="absolute inset-0 rounded-full border-4 border-gray-800/50"></div>
                <motion.div
                    className="absolute inset-0 rounded-full border-4 border-transparent border-t-blue-500 border-r-blue-400 border-b-cyan-400"
                    animate={{ rotate: 360 }}
                    transition={{
                    duration: 1.2,
                    ease: "linear",
                    repeat: Infinity,
                    }}
                />
            </div>
        
            {/* Loading message */}
            <motion.p 
                className="text-sm text-gray-400 text-center font-medium tracking-wide"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4 }}
            >
                {message}
            </motion.p>
          </div>
        </div>
      );
}