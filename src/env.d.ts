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
/// <reference types="vite/client" />

interface ImportMetaEnv {
  [key: string]: string | undefined; // Allow dynamic access to env vars
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

// For Electron context
declare global {
  interface Window {
    electron: {
      getEnv: (key: string) => string | undefined;
      getEnvironment: () => Record<string, string>;
    };
  }
}

export {};
