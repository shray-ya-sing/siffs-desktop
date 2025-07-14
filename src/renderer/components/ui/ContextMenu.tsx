// File: src/renderer/components/ui/ContextMenu.tsx
import React, { ReactNode, useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';

export interface ContextMenuItem {
  label: string;
  icon?: ReactNode;
  action: () => void;
  disabled?: boolean;
  separator?: boolean;
  destructive?: boolean;
}

interface ContextMenuProps {
  items: ContextMenuItem[];
  position: { x: number; y: number } | null;
  onClose: () => void;
  children?: ReactNode;
}

export const ContextMenu = ({
  items,
  position,
  onClose,
  children,
}: ContextMenuProps): React.ReactElement | null => {
  const menuRef = useRef<HTMLDivElement>(null);
  const [adjustedPosition, setAdjustedPosition] = useState<{ x: number; y: number } | null>(null);

  // Debug logging
  console.log('🎯 ContextMenu render:', {
    itemsCount: items.length,
    position,
    adjustedPosition,
    hasMenuRef: !!menuRef.current
  });

  useEffect(() => {
    if (!position) {
      setAdjustedPosition(null);
      return;
    }

    // Adjust position to keep menu within viewport
    const adjustPosition = () => {
      console.log('🔄 Adjusting position, menuRef.current:', !!menuRef.current);
      
      if (!menuRef.current) {
        // If ref isn't ready, set initial position and try again
        console.log('⏳ MenuRef not ready, setting initial position and retrying...');
        setAdjustedPosition({ x: position.x, y: position.y });
        setTimeout(adjustPosition, 10);
        return;
      }

      const menuRect = menuRef.current.getBoundingClientRect();
      const viewportWidth = window.innerWidth;
      const viewportHeight = window.innerHeight;

      let x = position.x;
      let y = position.y;

      console.log('📐 Menu dimensions:', { width: menuRect.width, height: menuRect.height });
      console.log('📐 Viewport size:', { width: viewportWidth, height: viewportHeight });
      console.log('📐 Initial position:', { x, y });

      // Adjust horizontal position if menu would overflow
      if (x + menuRect.width > viewportWidth) {
        x = viewportWidth - menuRect.width - 10;
      }

      // Adjust vertical position if menu would overflow
      if (y + menuRect.height > viewportHeight) {
        y = viewportHeight - menuRect.height - 10;
      }

      // Ensure menu doesn't go off-screen on the left or top
      x = Math.max(10, x);
      y = Math.max(10, y);

      console.log('📐 Final adjusted position:', { x, y });
      setAdjustedPosition({ x, y });
    };

    // Set initial position immediately to make menu visible
    setAdjustedPosition({ x: position.x, y: position.y });
    
    // Then adjust position after a brief delay
    setTimeout(adjustPosition, 0);

    // Handle clicks outside the menu
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        onClose();
      }
    };

    // Handle escape key
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose();
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleKeyDown);

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [position, onClose]);

  const menuContent = position && adjustedPosition ? (
    <div
      ref={menuRef}
      className="fixed z-50 min-w-48 bg-gray-800 border border-gray-600 rounded-md shadow-lg py-1"
      style={{
        left: adjustedPosition.x,
        top: adjustedPosition.y,
      }}
    >
      {items.map((item, index) => {
        if (item.separator) {
          return <div key={index} className="h-px bg-gray-600 my-1" />;
        }

        return (
          <button
            key={index}
            className={`
              w-full px-3 py-2 text-left text-sm flex items-center gap-2
              ${item.disabled 
                ? 'text-gray-500 cursor-not-allowed' 
                : item.destructive
                  ? 'text-red-400 hover:bg-red-500/20'
                  : 'text-gray-200 hover:bg-gray-700'
              }
              transition-colors duration-150
            `}
            onClick={() => {
              if (!item.disabled) {
                item.action();
                onClose();
              }
            }}
            disabled={item.disabled}
          >
            {item.icon && (
              <span className="w-4 h-4 flex-shrink-0">
                {item.icon}
              </span>
            )}
            <span className="flex-1">{item.label}</span>
          </button>
        );
      })}
    </div>
  ) : null;

  return (
    <>
      {children}
      {menuContent && createPortal(menuContent, document.body)}
    </>
  );
};

export default ContextMenu;
