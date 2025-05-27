import type { Configuration } from 'webpack';

import { rules } from './webpack.rules';
import { plugins } from './webpack.plugins';

// Remove the existing CSS rule if it exists
const cssRuleIndex = rules.findIndex(rule => 
  rule && typeof rule === 'object' && 'test' in rule && rule.test.toString().includes('.css')
);
if (cssRuleIndex !== -1) {
  rules.splice(cssRuleIndex, 1);
}

// Add the new CSS rule with postcss-loader
rules.push({
  test: /\.css$/,
  use: [
    { loader: 'style-loader' },
    { loader: 'css-loader' },
    { loader: 'postcss-loader' },
  ],
});

export const rendererConfig: Configuration = {
  module: {
    rules,
  },
  plugins,
  resolve: {
    extensions: ['.js', '.ts', '.jsx', '.tsx', '.css'],
  },
};
