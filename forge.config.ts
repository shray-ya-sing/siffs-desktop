import type { ForgeConfig } from '@electron-forge/shared-types';
import { MakerSquirrel } from '@electron-forge/maker-squirrel';
import { MakerZIP } from '@electron-forge/maker-zip';
import { MakerDeb } from '@electron-forge/maker-deb';
import { MakerRpm } from '@electron-forge/maker-rpm';
import { AutoUnpackNativesPlugin } from '@electron-forge/plugin-auto-unpack-natives';
import { WebpackPlugin } from '@electron-forge/plugin-webpack';
import { FusesPlugin } from '@electron-forge/plugin-fuses';
import { FuseV1Options, FuseVersion } from '@electron/fuses';
import {MakerDMG} from '@electron-forge/maker-dmg';
import { mainConfig } from './webpack.main.config';
import { rendererConfig } from './webpack.renderer.config';
import { buildPython } from './src/scripts/build-py';

const config: ForgeConfig = {
  packagerConfig: {
    asar: true,
    icon: process.platform === 'darwin' 
      ? './src/assets/icons/siffs-icon' // Electron will automatically add .icns
      : './src/assets/icons/siffs-icon-full.ico',
    // Pass environment variables to the packaged app
    extraResource: [
      '.env',      
      'resources/python/python-server',
      'resources/asgi.py',
      'LICENSE'
    ],
  },
  rebuildConfig: {},
  makers: [
    // Windows
    new MakerSquirrel({
      setupIcon: './src/assets/icons/siffs-icon-full.ico',
      iconUrl: 'https://raw.githubusercontent.com/cori-tan/siffs-desktop/main/src/assets/icons/siffs-icon-full.ico', // URL to icon for Add/Remove Programs
    }),
    // MacOS 
    new MakerZIP({}, ['darwin']),
    new MakerDMG({
      // Basic configuration
      name: 'SIFFS',
      icon: './src/assets/icons/siffs-icon.icns', // Path to your .icns file
      // Format and compression
      format: 'ULFO', // ULFO, UDZO, UDBZ, ULMO, etc.
    }, ['darwin']),
    // Linux
    new MakerRpm({}), 
    new MakerDeb({}),   
  ],
  plugins: [
    new AutoUnpackNativesPlugin({}),
    new WebpackPlugin({
      mainConfig,
      renderer: {
        config: rendererConfig,
        entryPoints: [
          {
            html: './src/index.html',
            js: './src/renderer.tsx', // Use .tsx instead of .ts
            name: 'main_window',
            preload: {
              js: './src/preload.ts',
            },
          },
        ],      
      },
    }),
    // Fuses are used to enable/disable various Electron functionality
    // at package time, before code signing the application
    new FusesPlugin({
      version: FuseVersion.V1,
      [FuseV1Options.RunAsNode]: false,
      [FuseV1Options.EnableCookieEncryption]: true,
      [FuseV1Options.EnableNodeOptionsEnvironmentVariable]: false,
      [FuseV1Options.EnableNodeCliInspectArguments]: false,
      [FuseV1Options.EnableEmbeddedAsarIntegrityValidation]: true,
      [FuseV1Options.OnlyLoadAppFromAsar]: true,
    }),
  ],
  publishers: [
    {
      name: '@electron-forge/publisher-github',
      config: {
        repository: {
          owner: 'cori-tan',  // Replace with your GitHub username
          name: 'siffs-desktop'         // Replace with your repository name
        },
        prerelease: true,  // Set to false if you don't want releases marked as pre-release
        authToken: process.env.GITHUB_TOKEN  // You'll need to set this environment variable
      }
    }
  ]
};

export default config;
