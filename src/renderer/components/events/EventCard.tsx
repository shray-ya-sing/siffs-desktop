import React from 'react';
import { cn } from '../../lib/utils';
import { Card } from '../ui/card';
import { Badge } from '../ui/badge';
import { Loader2 } from 'lucide-react';
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
  
  return (
    <Card 
      className={cn(
        "bg-[#1a2035]/50 backdrop-blur-sm shadow-sm py-0 overflow-hidden border",
        styles.card,
        className
      )}
      {...props}
    >
      <div className="p-2 flex items-center gap-2">
        {showBadge && (
          <Badge className={styles.badge}>
            {type.charAt(0).toUpperCase() + type.slice(1)}
          </Badge>
        )}
        <span 
          className={cn(
            "text-xs text-gray-200/90 font-mono",
            isStreaming && "animate-typewriter"
          )}
        >
          {message}
          </span>

          <div className="flex items-center gap-2 shrink-0">
            {isStreaming && <Loader2 className="h-3 w-3 animate-spin text-gray-400" />}
            {timestamp && (
                <span className="text-gray-400 text-2xs whitespace-nowrap">
                {new Date(timestamp).toLocaleTimeString()}
                </span>
            )}
        </div>
      </div>
    </Card>
  );
}

// Add typewriter animation styles
export const EventCardStyles = () => (
    <style>
      {`
        @keyframes typewriter {
          from { opacity: 0; }
          to { opacity: 1; }
        }
        .animate-typewriter {
          animation: typewriter 0.1s ease-in-out;
        }
      `}
    </style>
  );