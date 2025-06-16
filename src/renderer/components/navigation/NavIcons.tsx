import { useNavigate } from 'react-router-dom';
import { TechHomeIcon } from '../tech-icons/TechIcons';
interface NavIconsProps {
  className?: string;
}

export const NavIcons = ({ className = '' }: NavIconsProps) => {
  const navigate = useNavigate();

  return (
    <div className={`flex flex-col gap-3 ${className}`}>
      <button
        onClick={() => navigate('/')}
        className="p-2 rounded-full bg-gray-900/60 hover:bg-gray-800/70 backdrop-blur-sm 
                 border border-gray-700/50 shadow-lg transition-all duration-200
                 flex items-center justify-center"
        aria-label="Home"
      >
        <TechHomeIcon className="w-5 h-5 text-gray-300" />
      </button>
    </div>
  );
};