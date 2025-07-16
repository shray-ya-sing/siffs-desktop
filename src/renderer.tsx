/* eslint-disable @typescript-eslint/no-namespace */
/**
 * This file will automatically be loaded by webpack and run in the "renderer" context.
 * To learn more about the differences between the "main" and the "renderer" context in
 * Electron, visit:
 *
 * https://electronjs.org/docs/latest/tutorial/process-model
 *
 * By default, Node.js integration in this file is disabled. When enabling Node.js integration
 * in a renderer process, please be aware of potential security implications. You can read
 * more about security risks here:
 *
 * https://electronjs.org/docs/tutorial/security
 *
 * To enable Node.js integration in this file, open up `main.js` and enable the `nodeIntegration`
 * flag:
 *
 * ```
 *  // Create the browser window.
 *  mainWindow = new BrowserWindow({
 *    width: 800,
 *    height: 600,
 *    webPreferences: {
 *      nodeIntegration: true
 *    }
 *  });
 * ```
 */
import * as Sentry from "@sentry/electron/renderer";

Sentry.init({
  sendDefaultPii: true,
  integrations: [
  ],
});

import React from 'react';
import { createRoot, Root } from 'react-dom/client';
import { HashRouter, Routes, Route } from 'react-router-dom';
import { App } from './renderer/App';
import './index.css';
import './renderer/styles/globals.css';
// This is needed to use JSX in a .ts file
declare global {
  namespace JSX {
    interface IntrinsicElements {
      [elemName: string]: any;
    }
  }
}

// Get the root element
const container: HTMLElement | null = document.getElementById('root');

if (container) {
  const root: Root = createRoot(container);
  
  root.render(
    <React.StrictMode>
      <HashRouter>
        <Routes>
          <Route path="/*" element={<App />} />
        </Routes>
      </HashRouter>
    </React.StrictMode>
  );
}

// Keep the existing console log for debugging
console.log('👋 This message is being logged by "renderer.ts", included via webpack');