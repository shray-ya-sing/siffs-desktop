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

interface SiffsLogoProps {
  className?: string;
  width?: number;
  height?: number;
  size?: number;
}

export const SiffsLogo: React.FC<SiffsLogoProps> = ({ 
  className = '', 
  width, 
  height,
  size
}) => {
  // If size is provided, use it for both width and height
  // Otherwise, use the provided width/height or defaults
  const finalWidth = size || width || 32;
  const finalHeight = size || height || 38;
  return (
    <svg 
      width={finalWidth} 
      height={finalHeight} 
      viewBox="0 0 120 140" 
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      <defs>
        <linearGradient id="bubbleGradient" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" style={{stopColor:'#4F46E5', stopOpacity:1}} />
          <stop offset="50%" style={{stopColor:'#7C3AED', stopOpacity:1}} />
          <stop offset="100%" style={{stopColor:'#3B82F6', stopOpacity:1}} />
        </linearGradient>
      </defs>

      {/* Main S shape */}
      <path 
        d="M85 25 C95 15, 105 20, 100 35 C95 50, 75 55, 65 65 C55 75, 45 80, 50 95 C55 110, 75 105, 85 95 C90 90, 85 85, 80 90 C75 95, 65 98, 60 90 C55 82, 65 78, 70 82 C72 84, 70 86, 68 84 M25 115 C15 125, 5 120, 10 105 C15 90, 35 85, 45 75 C55 65, 65 60, 60 45 C55 30, 35 35, 25 45 C20 50, 25 55, 30 50 C35 45, 45 42, 50 50 C55 58, 45 62, 40 58 C38 56, 40 54, 42 56" 
        fill="url(#bubbleGradient)" 
        stroke="#1E293B" 
        strokeWidth="2" 
      />
    </svg>
  );
};

export default SiffsLogo;
