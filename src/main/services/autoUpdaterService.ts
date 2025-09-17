import { autoUpdater } from 'electron-updater';
import { BrowserWindow, dialog } from 'electron';
import log from 'electron-log';

/**
 * Auto-updater service for handling automatic updates from GitHub releases
 */
export class AutoUpdaterService {
  private mainWindow: BrowserWindow | null = null;

  constructor(mainWindow?: BrowserWindow) {
    if (mainWindow) {
      this.mainWindow = mainWindow;
    }

    // Configure auto-updater logging
    autoUpdater.logger = log;
    (autoUpdater.logger as typeof log).transports.file.level = 'info';
    
    // Allow pre-release updates
    autoUpdater.allowPrerelease = true;

    // Set up auto-updater event handlers
    this.setupEventHandlers();
  }

  private setupEventHandlers(): void {
    // Checking for updates
    autoUpdater.on('checking-for-update', () => {
      log.info('Checking for update...');
      this.sendStatusToWindow('Checking for update...');
    });

    // Update available
    autoUpdater.on('update-available', (info) => {
      log.info('Update available.');
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
      log.info('Update not available.');
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
      log.error('Error in auto-updater. ' + err);
      this.sendStatusToWindow('Error in auto-updater: ' + err);
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
