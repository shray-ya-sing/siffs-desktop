import React, { useEffect, useState } from 'react';
import { Loader2 } from 'lucide-react';

interface AppLoadingProps {
  onComplete?: () => void;
}

export default function AppLoading({ onComplete }: AppLoadingProps) {
  const [progress, setProgress] = useState(0);
  const [message, setMessage] = useState('Loading application...');

  // Progress bar animation effect
  useEffect(() => {
    const interval = setInterval(() => {
      setProgress(prev => {
        const newProgress = prev + 2;
        if (newProgress >= 100) {
          clearInterval(interval);
          if (onComplete) {
            // Small delay to show 100% before calling onComplete
            setTimeout(onComplete, 300);
          }
          return 100;
        }
        return newProgress;
      });
    }, 50);

    return () => clearInterval(interval);
  }, [onComplete]);

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-[#0a0f1a] text-white p-4">
      <div className="w-full max-w-md space-y-6 text-center">
        <div className="flex justify-center">
          <Loader2 className="h-12 w-12 animate-spin text-blue-400" />
        </div>
        <h1 className="text-2xl font-bold">Loading Cori</h1>
        <p className="text-gray-400">{message}</p>
        <div className="w-full bg-gray-700 rounded-full h-2.5">
          <div
            className="bg-blue-500 h-2.5 rounded-full transition-all duration-300 ease-out"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>
    </div>
  );
}