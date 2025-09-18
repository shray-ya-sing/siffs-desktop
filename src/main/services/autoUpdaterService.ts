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
import { autoUpdater } from 'electron-updater';
import { BrowserWindow, dialog } from 'electron';
import log from 'electron-log';

// Configure auto-updater IMMEDIATELY on import, before any other operations
autoUpdater.setFeedURL({
  provider: 'github',
  owner: 'shray-ya-sing',
  repo: 'siffs-desktop',
  private: false
});

// Set logging level immediately
autoUpdater.logger = log;
(autoUpdater.logger as typeof log).transports.file.level = 'info';

log.info('🔧 Auto-updater configured for GitHub releases: shray-ya-sing/siffs-desktop');

/**
 * Auto-updater service for handling automatic updates from GitHub releases
 */
export class AutoUpdaterService {
  private mainWindow: BrowserWindow | null = null;

  constructor(mainWindow?: BrowserWindow) {
    if (mainWindow) {
      this.mainWindow = mainWindow;
    }

    // Allow pre-release updates
    autoUpdater.allowPrerelease = false;
    
    // Add more detailed logging
    log.info('Auto-updater service initialized');
    log.info('Current app version (from package.json):', require('../../../package.json').version);
    try {
      log.info('App version (from app.getVersion()):', require('electron').app.getVersion());
    } catch (e) {
      log.warn('Could not get app version from electron.app.getVersion():', e instanceof Error ? e.message : String(e));
    }
    log.info('Auto download enabled:', autoUpdater.autoDownload);
    log.info('Allow prerelease:', autoUpdater.allowPrerelease);
    log.info('Repository: shray-ya-sing/siffs-desktop');
    
    // Configure GitHub token for private repository access
    // Note: For public repos, this shouldn't be necessary, but some repos require auth
    if (process.env.GITHUB_TOKEN) {
      autoUpdater.requestHeaders = {
        'Authorization': `token ${process.env.GITHUB_TOKEN}`
      };
      log.info('Auto-updater configured with GitHub authentication');
    } else {
      log.warn('No GITHUB_TOKEN found - auto-updater may fail if repo requires authentication');
    }

    // Set up auto-updater event handlers
    this.setupEventHandlers();
  }

  private setupEventHandlers(): void {
    // Checking for updates
    autoUpdater.on('checking-for-update', () => {
      log.info('🔍 Checking for update...');
      log.info('Repository: shray-ya-sing/siffs-desktop');
      this.sendStatusToWindow('Checking for update...');
    });

    // Update available
    autoUpdater.on('update-available', (info) => {
      log.info('✅ Update available!');
      log.info('Available version:', info.version);
      log.info('Release date:', info.releaseDate);
      log.info('Release notes:', info.releaseNotes);
      this.sendStatusToWindow('Update available.');
      
      // Optionally show a notification to the user
      if (this.mainWindow) {
        dialog.showMessageBox(this.mainWindow, {
          type: 'info',
          title: 'Update Available',
          message: `A new version (${info.version}) is available and will be downloaded in the background.`,
          buttons: ['OK']
        });
      }
    });

    // No update available
    autoUpdater.on('update-not-available', (info) => {
      log.info('ℹ️ Update not available.');
      log.info('Current version:', info.version);
      this.sendStatusToWindow('Update not available.');
    });

    // Download progress
    autoUpdater.on('download-progress', (progressObj) => {
      let log_message = "Download speed: " + progressObj.bytesPerSecond;
      log_message = log_message + ' - Downloaded ' + progressObj.percent + '%';
      log_message = log_message + ' (' + progressObj.transferred + "/" + progressObj.total + ')';
      log.info(log_message);
      this.sendStatusToWindow(log_message);
    });

    // Update downloaded
    autoUpdater.on('update-downloaded', (info) => {
      log.info('Update downloaded');
      this.sendStatusToWindow('Update downloaded');
      
      // Show dialog asking user to restart
      if (this.mainWindow) {
        dialog.showMessageBox(this.mainWindow, {
          type: 'info',
          title: 'Update Ready',
          message: `Update (${info.version}) has been downloaded. Restart the application to apply the update.`,
          buttons: ['Restart Now', 'Later'],
          defaultId: 0,
          cancelId: 1
        }).then((result) => {
          if (result.response === 0) {
            // User chose to restart now
            autoUpdater.quitAndInstall();
          }
        });
      }
    });

    // Error handling
    autoUpdater.on('error', (err) => {
      log.error('❌ Error in auto-updater:', err);
      log.error('Error message:', err.message);
      log.error('Error stack:', err.stack);
      log.error('Repository: shray-ya-sing/siffs-desktop');
      this.sendStatusToWindow('Error in auto-updater: ' + err.message);
      
      // Show error dialog in development
      if (process.env.NODE_ENV === 'development' && this.mainWindow) {
        dialog.showErrorBox('Auto-updater Error', `Failed to check for updates: ${err.message}`);
      }
    });
  }

  private sendStatusToWindow(text: string): void {
    if (this.mainWindow && this.mainWindow.webContents) {
      this.mainWindow.webContents.send('updater-message', text);
    }
  }

  /**
   * Check for updates manually
   */
  public checkForUpdates(): void {
    autoUpdater.checkForUpdatesAndNotify();
  }

  /**
   * Set the main window reference
   */
  public setMainWindow(mainWindow: BrowserWindow): void {
    this.mainWindow = mainWindow;
  }

  /**
   * Configure auto-updater settings
   */
  public configure(options: {
    checkForUpdatesOnStart?: boolean;
    autoDownload?: boolean;
    autoInstallOnAppQuit?: boolean;
  } = {}): void {
    const {
      checkForUpdatesOnStart = true,
      autoDownload = true,
      autoInstallOnAppQuit = true
    } = options;

    // Configure auto-updater settings
    autoUpdater.autoDownload = autoDownload;
    autoUpdater.autoInstallOnAppQuit = autoInstallOnAppQuit;

    // Check for updates on start if enabled
    if (checkForUpdatesOnStart) {
      // Check for updates after a short delay to let the app fully initialize
      setTimeout(() => {
        this.checkForUpdates();
      }, 5000); // 5 second delay
    }
  }

  /**
   * Force quit and install update
   */
  public quitAndInstall(): void {
    autoUpdater.quitAndInstall();
  }
}
