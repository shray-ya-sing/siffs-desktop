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
import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';

interface AppLoadingProps {
  onComplete?: () => void;
  message?: string;
}

export default function AppLoading({ onComplete, message = 'Preparing your experience...' }: AppLoadingProps) {
  const [progress, setProgress] = useState(0);
  const [isComplete, setIsComplete] = useState(false);

  // Progress bar animation effect
  useEffect(() => {
    const interval = setInterval(() => {
      setProgress(prev => {
        // Slow down as we approach 100%
        const increment = prev < 90 ? 2 : 0.5;
        const newProgress = Math.min(prev + increment, 100);
        
        if (newProgress >= 100) {
          clearInterval(interval);
          setIsComplete(true);
          if (onComplete) {
            // Small delay to show 100% before calling onComplete
            setTimeout(onComplete, 300);
          }
          return 100;
        }
        return newProgress;
      });
    }, 30);

    return () => clearInterval(interval);
  }, [onComplete]);

  return (
    <div className="flex flex-col items-center justify-center min-h-screen p-6">
      <div className="w-full max-w-md space-y-6">
        {/* Modern rectangular progress bar */}
        <div className="w-full">
          <div className="relative w-full h-3 bg-gray-800/50 overflow-hidden">
            <motion.div 
              className="h-full bg-gradient-to-r from-blue-500 via-blue-400 to-cyan-400"
              initial={{ width: '0%' }}
              animate={{ width: `${progress}%` }}
              transition={{
                duration: 0.6,
                ease: [0.16, 1, 0.3, 1],
              }}
            >
              {/* Shimmer effect */}
              <div className="absolute inset-y-0 left-0 w-1/3 bg-white/30 animate-shimmer" 
                style={{
                  transform: 'skewX(-20deg)',
                  boxShadow: '0 0 30px 10px rgba(255, 255, 255, 0.2)'
                }}
              />
            </motion.div>
            
            {/* Progress percentage */}
            <div className="absolute inset-0 flex items-center justify-end pr-2">
              <span className="text-xs font-mono text-white/70">
                {Math.round(progress)}%
              </span>
            </div>
          </div>
        </div>
        
        {/* Loading message */}
        <motion.p 
          className="text-sm text-gray-400 text-center font-medium tracking-wide"
          initial={{ opacity: 0, y: 5 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2, duration: 0.4 }}
        >
          {isComplete ? 'Almost there...' : message}
        </motion.p>
      </div>
    </div>
  );
}