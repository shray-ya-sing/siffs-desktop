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
import React, { useEffect } from 'react';
import { motion } from 'framer-motion';

interface AuthLoadingProps {
  message?: string;
}

export default function AuthLoading({ message = 'Signing in...' }: AuthLoadingProps) {
    return (
        <div className="w-full h-full flex items-center justify-center p-6">
          <div className="max-w-xs space-y-6 flex flex-col items-center">
            {/* Spinner and message */}
            {/* Spinner with gradient */}
            <div className="relative w-16 h-16">
                <div className="absolute inset-0 rounded-full border-4 border-gray-800/50"></div>
                <motion.div
                    className="absolute inset-0 rounded-full border-4 border-transparent border-t-blue-500 border-r-blue-400 border-b-cyan-400"
                    animate={{ rotate: 360 }}
                    transition={{
                    duration: 1.2,
                    ease: "linear",
                    repeat: Infinity,
                    }}
                />
            </div>
        
            {/* Loading message */}
            <motion.p 
                className="text-sm text-gray-400 text-center font-medium tracking-wide"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4 }}
            >
                {message}
            </motion.p>
          </div>
        </div>
      );
}