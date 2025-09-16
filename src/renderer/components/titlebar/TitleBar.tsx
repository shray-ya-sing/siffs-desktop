import React from 'react';
import { MinusIcon, XMarkIcon } from '@heroicons/react/24/outline';
import { NavIcons } from '../navigation/NavIcons';
import { SiffsLogo } from '../icons/SiffsLogo';

interface TitleBarProps {
  title?: string;
  className?: string;
  showNavigation?: boolean;
}

export const TitleBar: React.FC<TitleBarProps> = ({ 
  title = 'Volute', 
  className = '',
  showNavigation = true
}) => {
  const handleMinimize = () => {
    (window as any).electron?.window?.minimize?.();
  };

  const handleClose = () => {
    (window as any).electron?.window?.close?.();
  };

  return (
    <>
      {/* Subtle morphism background elements */}
      <style>{`
        .titlebar-morphism::before {
          content: '';
          position: absolute;
          top: 50%;
          left: 20%;
          width: 40px;
          height: 40px;
          background: rgba(255, 255, 255, 0.3);
          border-radius: 50%;
          filter: blur(15px);
          animation: titlebar-float 6s ease-in-out infinite;
          pointer-events: none;
        }
        
        .titlebar-morphism::after {
          content: '';
          position: absolute;
          top: 50%;
          right: 20%;
          width: 30px;
          height: 30px;
          background: rgba(255, 255, 255, 0.2);
          border-radius: 50%;
          filter: blur(10px);
          animation: titlebar-float 8s ease-in-out infinite reverse;
          pointer-events: none;
        }
        
        @keyframes titlebar-float {
          0%, 100% {
            transform: translateY(-50%) translateX(0px) scale(1);
          }
          50% {
            transform: translateY(-50%) translateX(5px) scale(1.1);
          }
        }
      `}</style>
    <div 
      className={`
        titlebar-morphism
        fixed top-0 left-0 right-0 z-[9999] 
        h-8 flex items-center justify-between px-4
        select-none
        ${className}
      `}
      style={{
        // This is the key CSS property that makes the area draggable
        WebkitAppRegion: 'drag',
        background: 'linear-gradient(135deg, #F8F9FA 0%, #F5F6F8 25%, #F2F4F6 50%, #EFF1F4 75%, #ECEEF2 100%)',
        backdropFilter: 'blur(10px)',
        WebkitBackdropFilter: 'blur(10px)',
        borderBottom: '1px solid rgba(255, 255, 255, 0.3)',
        boxShadow: '0 4px 16px rgba(0, 0, 0, 0.04), inset 0 1px 0 rgba(255, 255, 255, 0.8), inset 0 -1px 0 rgba(255, 255, 255, 0.4)',
        position: 'relative',
        overflow: 'hidden'
      } as React.CSSProperties}
    >
      {/* Left side - Logo and Navigation Icons */}
      <div 
        className="flex items-center space-x-3"
        style={{
          // Make logo and navigation clickable (not draggable)
          WebkitAppRegion: 'no-drag'
        } as React.CSSProperties}
      >
        {/* App Logo */}
        <SiffsLogo 
          className="text-gray-600 hover:text-gray-800 transition-colors" 
          size={20}
        />
        
        {/* Navigation Icons */}
        {showNavigation && <NavIcons />}
      </div>

      {/* Right side - Window controls */}
      <div 
        className="flex items-center space-x-2"
        style={{
          // Make buttons clickable (not draggable)
          WebkitAppRegion: 'no-drag'
        } as React.CSSProperties}
      >
        <button
          onClick={handleMinimize}
          className="p-1 rounded hover:bg-gray-200/50 transition-colors"
          title="Minimize"
        >
          <MinusIcon className="w-4 h-4 text-gray-600 hover:text-gray-800" />
        </button>
        <button
          onClick={handleClose}
          className="p-1 rounded hover:bg-red-200/50 transition-colors"
          title="Close"
        >
          <XMarkIcon className="w-4 h-4 text-gray-600 hover:text-red-600" />
        </button>
      </div>
    </div>
    </>
  );
};
