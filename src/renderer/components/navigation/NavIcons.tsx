/*
 * Siffs - Fast File Search Desktop Application
 * Copyright (C) 2025  Siffs
 * 
 * Contact: github.suggest277@passinbox.com
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */
import { useNavigate } from 'react-router-dom';
import { TechHomeIcon, TechSignOutIcon } from '../tech-icons/TechIcons';
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
        className="p-1.5 rounded hover:bg-gray-200/50 transition-all duration-200
                 flex items-center justify-center"
        aria-label="Home"
      >
        <TechHomeIcon className="w-4 h-4 text-gray-600 hover:text-gray-800" />
      </button>
      <button
        onClick={handleSignOut}
        className="p-1.5 rounded hover:bg-red-200/50 transition-all duration-200
                 flex items-center justify-center group"
        aria-label="Sign Out"
      >
        <TechSignOutIcon className="w-4 h-4 text-red-500 group-hover:text-red-700" />
      </button>
    </div>
  );
};