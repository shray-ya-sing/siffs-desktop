import React from 'react';
import { MinusIcon, XMarkIcon } from '@heroicons/react/24/outline';
import { NavIcons } from '../navigation/NavIcons';
// Use SVG from assets folder

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
    <div 
      className={`
        fixed top-0 left-0 right-0 z-[9999] 
        h-8 bg-[#0a0a0a] border-b border-gray-800
        flex items-center justify-between px-4
        select-none
        ${className}
      `}
      style={{
        // This is the key CSS property that makes the area draggable
        WebkitAppRegion: 'drag'
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
        <img 
          src={require('../../../assets/icons/svg/volute_icon.svg').default || require('../../../assets/icons/svg/volute_icon.svg')} 
          alt="Volute" 
          className="w-5 h-5" 
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
          className="p-1 rounded hover:bg-gray-700 transition-colors"
          title="Minimize"
        >
          <MinusIcon className="w-4 h-4 text-gray-400 hover:text-white" />
        </button>
        <button
          onClick={handleClose}
          className="p-1 rounded hover:bg-red-600 transition-colors"
          title="Close"
        >
          <XMarkIcon className="w-4 h-4 text-gray-400 hover:text-white" />
        </button>
      </div>
    </div>
  );
};
