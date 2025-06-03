// src/components/header/Subheader.tsx
import { ChevronRightIcon } from '@heroicons/react/24/outline';
import { cn } from '../../lib/utils';

interface SubheaderStep {
  label: string;
  isActive?: boolean;
  isCompleted?: boolean;
}

interface SubheaderProps {
  steps: SubheaderStep[];
  className?: string;
}

export const Subheader = ({ steps, className }: SubheaderProps) => {
  return (
    <div className={cn("bg-slate-800 border-b border-slate-700", className)}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <nav className="flex items-center py-3" aria-label="Progress">
          <ol className="flex items-center space-x-4">
            {steps.map((step, index) => (
              <li key={step.label} className="flex items-center">
                {index > 0 && (
                  <ChevronRightIcon 
                    className="h-5 w-5 text-slate-500 mx-2" 
                    aria-hidden="true" 
                  />
                )}
                <span
                  className={cn(
                    "text-sm font-medium",
                    step.isActive 
                      ? "text-blue-400" 
                      : step.isCompleted 
                        ? "text-slate-400" 
                        : "text-slate-500"
                  )}
                >
                  {step.label}
                </span>
              </li>
            ))}
          </ol>
        </nav>
      </div>
    </div>
  );
};