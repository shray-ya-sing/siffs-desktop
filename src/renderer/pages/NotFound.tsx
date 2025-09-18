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
import { Link } from 'react-router-dom';

export function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-[#0a0f1a] text-white p-4">
      <h2 className="text-2xl font-bold mb-4">404 - Page Not Found</h2>
      <p className="mb-4">The page you're looking for doesn't exist or has been moved.</p>
      <Link 
        to="/" 
        className="px-4 py-2 bg-blue-600/80 hover:bg-blue-700/80 rounded-md transition-colors border border-blue-500/30"
      >
        Go to Home
      </Link>
      <div className="mt-8 p-4 bg-[#1a2035]/30 rounded-md max-w-md border border-[#ffffff0f]">
        <h3 className="font-semibold mb-2">Available Routes:</h3>
        <ul className="list-disc list-inside space-y-1">
          <li><Link to="/" className="text-blue-400 hover:underline">/ - Home</Link></li>
          <li><Link to="/settings" className="text-blue-400 hover:underline">/settings</Link></li>
          {/* Add more routes as needed */}
        </ul>
      </div>
    </div>
  );
}