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
  // Modern AI/Tech color palette
  extracting: {
    badge: 'bg-cyan-500/20 text-cyan-300 border-cyan-500/30',
    card: 'bg-gradient-to-br from-cyan-950/30 to-cyan-900/20',
    glow: 'shadow-cyan-500/10'
  },
  checking: {
    badge: 'bg-amber-500/20 text-amber-300 border-amber-500/30',
    card: 'bg-gradient-to-br from-amber-950/30 to-amber-900/20',
    glow: 'shadow-amber-500/10'
  },
  completed: {
    badge: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
    card: 'bg-gradient-to-br from-emerald-950/30 to-emerald-900/20',
    glow: 'shadow-emerald-500/10'
  },
  analyzing: {
    badge: 'bg-violet-500/20 text-violet-300 border-violet-500/30',
    card: 'bg-gradient-to-br from-violet-950/30 to-violet-900/20',
    glow: 'shadow-violet-500/10'
  },
  generating: {
    badge: 'bg-blue-500/20 text-blue-300 border-blue-500/30',
    card: 'bg-gradient-to-br from-blue-950/30 to-blue-900/20',
    glow: 'shadow-blue-500/10'
  },
  executing: {
    badge: 'bg-purple-500/20 text-purple-300 border-purple-500/30',
    card: 'bg-gradient-to-br from-purple-950/30 to-purple-900/20',
    glow: 'shadow-purple-500/10'
  },
  reviewing: {
    badge: 'bg-indigo-500/20 text-indigo-300 border-indigo-500/30',
    card: 'bg-gradient-to-br from-indigo-950/30 to-indigo-900/20',
    glow: 'shadow-indigo-500/10'
  },
  retrying: {
    badge: 'bg-orange-500/20 text-orange-300 border-orange-500/30',
    card: 'bg-gradient-to-br from-orange-950/30 to-orange-900/20',
    glow: 'shadow-orange-500/10'
  },
  info: {
    badge: 'bg-slate-500/20 text-slate-300 border-slate-500/30',
    card: 'bg-gradient-to-br from-slate-950/30 to-slate-900/20',
    glow: 'shadow-slate-500/10'
  },
  error: {
    badge: 'bg-red-500/20 text-red-300 border-red-500/30',
    card: 'bg-gradient-to-br from-red-950/30 to-red-900/20',
    glow: 'shadow-red-500/10'
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
            "relative overflow-hidden py-0 backdrop-blur-sm border-none",
            styles.card,
            styles.glow,
            className,
            isStreaming && "pr-2"
          )}
          style={{
            backdropFilter: 'blur(8px)',
            borderRadius: '0.5rem',
            border: 'none',
          }}
          {...props}
        >
          {showShimmer && (
            <div className={cn(
              "absolute inset-0 rounded-lg animate-shimmer",
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