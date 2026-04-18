import { defineConfig } from 'astro/config';
import mdx from '@astrojs/mdx';
import { resolve } from 'node:path';

// Resolved at build time from astro/ directory (where npm run build executes)
const DATA_ROOT = resolve(process.cwd(), '../docs/data');

export default defineConfig({
  site: 'https://yuyangxueed.github.io',
  base: '/Linnet',
  integrations: [mdx()],
  output: 'static',
  vite: {
    define: {
      __DATA_ROOT__: JSON.stringify(DATA_ROOT),
    }
  }
});
