import { useNavigate, useLocation } from 'react-router-dom';
import {
  TechHomeIcon,
  TechSpreadsheetIcon,
  TechHistoryIcon,
  TechBookmarkIcon,
  TechHelpIcon,
  TechSettingsIcon,
} from '../components/tech-icons/TechIcons';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '../components/ui/tooltip';
import { useState } from 'react';

interface NavButtonProps {
  icon: React.ReactNode;
  label: string;
  href: string;
  isActive: boolean;
  onClick: (e: React.MouseEvent, href: string) => void;
}

function NavButton({ icon, label, href, isActive, onClick }: NavButtonProps) {
  const [isNavigating, setIsNavigating] = useState(false);
  
  const handleClick = async (e: React.MouseEvent) => {
    e.preventDefault();
    if (isNavigating) return;
    
    setIsNavigating(true);
    try {
      await onClick(e, href);
    } finally {
      setTimeout(() => setIsNavigating(false), 500);
    }
  };
  
  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <div 
            className={`p-1 rounded-lg transition-all duration-300 ${
              isActive 
                ? 'bg-blue-600/30 border-blue-500/50' 
                : 'bg-[#1a2035]/20 border-[#ffffff0f] hover:bg-[#1a2035]/40'
            } border backdrop-blur-sm ${isNavigating ? 'opacity-75' : ''}`}
          >
            <button
              onClick={handleClick}
              disabled={isNavigating}
              className={`h-8 w-8 flex items-center justify-center rounded-md transition-colors ${
                isActive 
                  ? 'text-white' 
                  : 'text-gray-400 hover:text-white hover:bg-[#ffffff10]'
              }`}
              aria-label={isNavigating ? 'Loading...' : label}
            >
              {isNavigating ? (
                <svg
                  className="h-4 w-4 animate-spin text-current"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  ></circle>
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  ></path>
                </svg>
              ) : (
                icon
              )}
            </button>
          </div>
        </TooltipTrigger>
        <TooltipContent side="right" sideOffset={10}>
          <p>{isNavigating ? 'Loading...' : label}</p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

export function Sidebar() {
  const location = useLocation();
  const navigate = useNavigate();

  const navItems = [
    { icon: <TechHomeIcon />, label: 'Dashboard', href: '/' },
    { icon: <TechSpreadsheetIcon />, label: 'Excel', href: '/excel' },
    // Add more navigation items as needed
  ];

  const handleNavigation = async (e: React.MouseEvent, href: string) => {
    e.preventDefault();
    navigate(href);
  };

  const handleSignOut = () => {
    document.cookie = 'auth-token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT';
    navigate('/auth/login');
  };

  return (
    <div className="w-16 border-r border-[#ffffff0f] flex flex-col items-center py-4 bg-[#1a2035]/20 backdrop-blur-md" style={{ position: 'relative' }}>
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <div className="mb-6">
              <div 
                className="h-10 w-10 rounded-full flex items-center justify-center bg-blue-600/30 backdrop-blur-sm border border-[#ffffff0f] shadow-[0_0_15px_rgba(59,130,246,0.3)] cursor-pointer overflow-hidden" 
                onClick={() => navigate('/')}
              >
                <img 
                  src="/assets/cori-logo.svg" 
                  alt="Cori Logo" 
                  className="h-6 w-6 object-contain"
                />
              </div>
            </div>
          </TooltipTrigger>
          <TooltipContent side="right" sideOffset={10}>
            <p>Home</p>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>

      <div className="flex flex-col items-center gap-4 flex-1">
        {navItems.map((item) => (
          <NavButton
            key={item.href}
            icon={item.icon}
            label={item.label}
            href={item.href}
            isActive={location.pathname === item.href}
            onClick={handleNavigation}
          />
        ))}
      </div>

      <div className="mt-auto flex flex-col items-center gap-4">
        <NavButton
          icon={<TechSettingsIcon />}
          label="Settings"
          href="/settings"
          isActive={location.pathname === '/settings'}
          onClick={handleNavigation}
        />
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <div className="p-1 rounded-lg bg-[#1a2035]/20 border border-[#ffffff0f] hover:bg-[#1a2035]/40 backdrop-blur-sm transition-all duration-300">
                <button
                  onClick={handleSignOut}
                  className="h-8 w-8 flex items-center justify-center rounded-md text-gray-400 hover:text-white hover:bg-[#ffffff10] transition-colors"
                  aria-label="Sign out"
                >
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    width="16"
                    height="16"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                    <polyline points="16 17 21 12 16 7" />
                    <line x1="21" y1="12" x2="9" y2="12" />
                  </svg>
                </button>
              </div>
            </TooltipTrigger>
            <TooltipContent side="right" sideOffset={10}>
              <p>Sign out</p>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </div>
    </div>
  );
}