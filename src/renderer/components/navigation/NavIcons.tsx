import { useNavigate } from 'react-router-dom';
import { TechHomeIcon, TechSettingsIcon, TechSignOutIcon } from '../tech-icons/TechIcons';
import { useAuth } from '../../providers/AuthProvider';

interface NavIconsProps {
  className?: string;
}

export const NavIcons = ({ className = '' }: NavIconsProps) => {
  const navigate = useNavigate();
  const { signOut } = useAuth();

  const handleSignOut = async () => {
    try {
      await signOut();
      navigate('/auth/login', { replace: true });
    } catch (error) {
      console.error('Sign out error:', error);
      // Even if there's an error, redirect to login
      navigate('/auth/login', { replace: true });
    }
  };

  return (
    <div className={`flex flex-row gap-2 ${className}`}>
      <button
        onClick={() => navigate('/')}
        className="p-1.5 rounded hover:bg-gray-700/50 transition-all duration-200
                 flex items-center justify-center"
        aria-label="Home"
      >
        <TechHomeIcon className="w-4 h-4 text-gray-300 hover:text-white" />
      </button>
      <button
        onClick={() => navigate('/settings')}
        className="p-1.5 rounded hover:bg-gray-700/50 transition-all duration-200
                 flex items-center justify-center"
        aria-label="Settings"
      >
        <TechSettingsIcon className="w-4 h-4 text-gray-300 hover:text-white" />
      </button>
      <button
        onClick={handleSignOut}
        className="p-1.5 rounded hover:bg-red-700/50 transition-all duration-200
                 flex items-center justify-center group"
        aria-label="Sign Out"
      >
        <TechSignOutIcon className="w-4 h-4 text-red-300 group-hover:text-red-200" />
      </button>
    </div>
  );
};