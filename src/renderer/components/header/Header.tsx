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
import React from 'react';
import { Bars3Icon, MagnifyingGlassIcon } from '@heroicons/react/24/outline'
import { SiffsLogo } from '../icons/SiffsLogo'

export const Header = () => {
  return (
    <header className="sticky top-0 z-10 bg-slate-900 border-b border-slate-800 p-4">
      <div className="flex items-center justify-between max-w-7xl mx-auto">
        <div className="flex items-center space-x-4">
          <SiffsLogo className="text-white" width={32} height={38} />
          <button className="text-slate-400 hover:text-white">
            <Bars3Icon className="h-6 w-6" />
          </button>
          <h1 className="text-xl font-semibold text-white">Dashboard</h1>
        </div>
        <div className="relative w-1/3">
          <input
            type="text"
            placeholder="Search..."
            className="w-full bg-slate-800 text-white rounded-lg py-2 px-4 pl-10 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <MagnifyingGlassIcon className="absolute left-3 top-2.5 h-5 w-5 text-slate-500" />
        </div>
      </div>
    </header>
  );
};

export default Header;