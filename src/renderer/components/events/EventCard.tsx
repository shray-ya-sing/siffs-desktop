import React, { useEffect, useState } from 'react';
import { cn } from '../../lib/utils';
import { Card } from '../ui/card';
import { Badge } from '../ui/badge';
import { Loader2 } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
// Types of events
export type EventType = 
  | 'extracting' 
  | 'checking' 
  | 'completed'
  | 'analyzing' 
  | 'generating' 
  | 'executing' 
  | 'reviewing' 
  | 'retrying'
  | 'info'
  | 'error';

export interface EventCardProps {
  type: EventType;
  message: string;
  className?: string;
  showBadge?: boolean;
  isStreaming?: boolean;
  timestamp?: number;
  isActive?: boolean;
}

const typeStyles = {
  // Your custom types
  extracting: {
    badge: 'bg-blue-600/40 text-blue-300/90',
    card: 'border-blue-500/20'
  },
  checking: {
    badge: 'bg-yellow-600/40 text-yellow-300/90',
    card: 'border-yellow-500/20'
  },
  completed: {
    badge: 'bg-green-600/40 text-green-300/90',
    card: 'border-green-500/20'
  },
  // Original types for reference
  analyzing: {
    badge: 'bg-yellow-600/40 text-yellow-300/90',
    card: 'border-yellow-500/20'
  },
  generating: {
    badge: 'bg-blue-600/40 text-blue-300/90',
    card: 'border-blue-500/20'
  },
  executing: {
    badge: 'bg-green-600/40 text-green-300/90',
    card: 'border-green-500/20'
  },
  reviewing: {
    badge: 'bg-purple-600/40 text-purple-300/90',
    card: 'border-purple-500/20'
  },
  retrying: {
    badge: 'bg-gray-600/40 text-gray-300/90',
    card: 'border-gray-500/20'
  },
  info: {
    badge: 'bg-gray-600/40 text-gray-300/90',
    card: 'border-gray-500/20'
  },
  error: {
    badge: 'bg-red-600/40 text-red-300/90',
    card: 'border-red-500/20'
  }
};

export function EventCard({
  type,
  message,
  className,
  showBadge = true,
  isStreaming = false,
  timestamp,
  ...props
}: EventCardProps & React.HTMLAttributes<HTMLDivElement>) {
  const styles = typeStyles[type] || typeStyles.info;
  const [showShimmer, setShowShimmer] = useState(false);
  
  // Toggle shimmer effect when isStreaming changes
  useEffect(() => {
    if (isStreaming) {
      setShowShimmer(true);
    } else {
      const timer = setTimeout(() => setShowShimmer(false), 1000);
      return () => clearTimeout(timer);
    }
  }, [isStreaming]);
  
  // Format time to show only hours and minutes
  const formatTime = (ts: number) => {
    return new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };
  
  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.2 }}
        className="relative"
      >
        <Card 
          className={cn(
            "relative overflow-hidden py-0 border bg-[#2a2a2a]/80 backdrop-blur-sm",
            styles.card,
            className,
            isStreaming && "pr-2"
          )}
          style={{
            background: 'rgba(42, 42, 42, 0.8)',
            backdropFilter: 'blur(8px)',
            borderRadius: '1rem',
          }}
          {...props}
        >
          {showShimmer && (
            <div className={cn(
              "absolute inset-0 rounded-xl animate-shimmer",
              isStreaming ? "opacity-30" : "opacity-0"
            )} 
            style={{
              background: `linear-gradient(90deg, transparent, rgba(255,255,255,0.1), transparent)`,
              backgroundSize: '200% 100%',
            }}
            />
          )}
          
          <div className="p-2 flex items-center justify-between w-full">
            <div className="flex items-center gap-2 overflow-hidden">
              {showBadge && (
                <Badge className={cn(styles.badge, "shrink-0")}>
                  {type.charAt(0).toUpperCase() + type.slice(1)}
                </Badge>
              )}
              <span className="text-xs text-gray-200/90 truncate">
                {message}
              </span>
            </div>

            <div className="flex items-center gap-2 shrink-0 ml-2">
              {/*isStreaming && <Loader2 className="h-3 w-3 animate-spin text-gray-400" />*/}
              {timestamp && (
                <span className="text-gray-400 text-[10px] opacity-60 whitespace-nowrap">
                  {formatTime(timestamp)}
                </span>
              )}
            </div>
          </div>
        </Card>
      </motion.div>
    </AnimatePresence>
  );
}

// Add shimmer animation styles
export const EventCardStyles = () => (
  <style>
    {`
      @keyframes shimmer {
        0% {
          background-position: -200% 0;
        }
        100% {
          background-position: 200% 0;
        }
      }
      .animate-shimmer {
        animation: shimmer 2s infinite linear;
      }
    `}
  </style>
);