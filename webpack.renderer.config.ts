import type { Configuration, RuleSetRule } from 'webpack';

import { rules } from './webpack.rules';
import { plugins } from './webpack.plugins';

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
  }
);

export const rendererConfig: Configuration = {
  target: 'web',
  module: {
    rules: rules as RuleSetRule[],
  },
  plugins,
  resolve: {
    extensions: ['.js', '.ts', '.jsx', '.tsx', '.css', '.json'],
  },
  // Add these new configurations
  node: {
    __dirname: false,
    __filename: false,
  },
  externals: {
    // Add any native modules you're using
  },
};
