import fs from 'node:fs/promises';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const bundledModules = process.env.CODEX_NODE_MODULES;
if (!bundledModules) {
  throw new Error('CODEX_NODE_MODULES is required');
}
const sharp = require(path.join(bundledModules, 'sharp'));

const input = fileURLToPath(new URL('../output/figures/figure-2-13-system-architecture-v8.svg', import.meta.url));
const pngOutput = fileURLToPath(new URL('../output/figures/figure-2-13-system-architecture-v8.png', import.meta.url));
const jpegOutput = fileURLToPath(new URL('../output/figures/figure-2-13-system-architecture-v8.jpg', import.meta.url));

const svg = await fs.readFile(input);
const raster = sharp(svg, { density: 180 }).flatten({ background: '#ffffff' });
await raster.clone().png({ compressionLevel: 9 }).toFile(pngOutput);
await raster.clone().jpeg({ quality: 96, chromaSubsampling: '4:4:4' }).toFile(jpegOutput);
