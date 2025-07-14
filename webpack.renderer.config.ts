import type { Configuration, RuleSetRule } from 'webpack';
import { rules } from './webpack.rules';
import { plugins } from './webpack.plugins';
import * as path from 'path';
import * as webpack from 'webpack';
import CopyWebpackPlugin from 'copy-webpack-plugin';
import { fileURLToPath } from 'url';
import * as process from 'process';
import * as dotenv from 'dotenv';

// Get __dirname equivalent in ES modules
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Load environment variables
const envPath = path.resolve(__dirname, '.env');
let envVars = {};
try {
  const result = dotenv.config({ path: envPath });
  envVars = result.parsed || {};
} catch (error) {
  console.warn('Failed to load .env file:', error);
}

// Merge with process.env
const mergedEnv = { ...process.env, ...envVars };

// Remove the CSS rule that's causing issues
const cssRuleIndex = rules.findIndex(rule => 
  rule && 
  typeof rule === 'object' && 
  'test' in rule && 
  rule.test && 
  rule.test.toString().includes('.css')
);

if (cssRuleIndex !== -1) {
  rules.splice(cssRuleIndex, 1);
}

// Add a new CSS rule that works with CSS modules
rules.push(
  {
    test: /\.css$/i,
    use: [
      'style-loader',
      'css-loader',
      'postcss-loader',
    ],
  },
  // Add support for TypeScript and JSX
  {
    test: /\.(js|jsx|ts|tsx)$/,
    exclude: /node_modules/,
    use: {
      loader: 'babel-loader',
      options: {
        presets: [
          '@babel/preset-env',
          ['@babel/preset-react', { runtime: 'automatic' }],
          '@babel/preset-typescript'
        ]
      }
    }
  },
  // Add support for images
  {
    test: /\.(png|jpe?g|gif)$/i,
    type: 'asset/resource',
  }
);

export const rendererConfig: Configuration = {
  target: 'web',
  module: {
    rules: rules as RuleSetRule[],
  },
  plugins: [
    ...plugins,
    new CopyWebpackPlugin({
      patterns: [
        {
          from: path.resolve(__dirname, 'src/assets'),
          to: 'assets',
        },
      ],
    }),
    new webpack.DefinePlugin({
      'process.env': JSON.stringify({
        NODE_ENV: mergedEnv.NODE_ENV || 'development'
      })
    })
  ],
  resolve: {
    extensions: ['.js', '.ts', '.jsx', '.tsx', '.css', '.json'],
    fallback: {
      // Disable all Node.js core modules in the renderer process
      path: false,
      os: false,
      crypto: false,
      fs: false,
      stream: false,
      util: false,
      buffer: false,
      vm: false,
      http: false,
      https: false,
      url: false,
      assert: false
    },
    alias: {
      // Add any other aliases needed for your application
      react: path.resolve(__dirname, 'node_modules/react')
    },
    modules: [
      'node_modules',
      path.resolve(__dirname, 'node_modules')
    ]
  },
  // Node.js configuration
  node: {
    __dirname: false,
    __filename: false,
    global: true,
  },
  // Exclude Node.js core modules and native modules
  externals: {
    'path': 'commonjs path',
    'os': 'commonjs os',
    'crypto': 'commonjs crypto',
    'fs': 'commonjs fs',
    'stream': 'commonjs stream',
    'util': 'commonjs util',
    'buffer': 'commonjs buffer',
    'vm': 'commonjs vm',
    'http': 'commonjs http',
    'https': 'commonjs https',
    'url': 'commonjs url',
    'assert': 'commonjs assert',
    'electron': 'commonjs electron'
  },
  // Configure global variables
  output: {
    globalObject: 'this',
  },
};
