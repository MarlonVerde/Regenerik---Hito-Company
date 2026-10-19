import { mkdir, copyFile } from 'node:fs/promises';
import sharp from 'sharp';

await mkdir('uis/web/assets', { recursive: true });
for (const width of [480, 768, 1152]) {
  await sharp('Brasaland-company.md/Brasaland.png')
    .resize({ width })
    .webp({ quality: 80 })
    .toFile(`uis/web/assets/brasaland-${width}.webp`);
}
await mkdir('uis/backoffice/assets', { recursive: true });
for (const [source, target] of [
  ['@fontsource-variable/space-grotesk/files/space-grotesk-latin-wght-normal.woff2', 'space-grotesk-latin.woff2'],
  ['@fontsource/ibm-plex-mono/files/ibm-plex-mono-latin-400-normal.woff2', 'ibm-plex-mono-400-latin.woff2'],
  ['@fontsource/ibm-plex-mono/files/ibm-plex-mono-latin-600-normal.woff2', 'ibm-plex-mono-600-latin.woff2'],
]) {
  await copyFile(`node_modules/${source}`, `uis/backoffice/assets/${target}`);
}
await copyFile('node_modules/@fontsource-variable/space-grotesk/LICENSE', 'uis/backoffice/assets/space-grotesk.LICENSE');
await copyFile('node_modules/@fontsource/ibm-plex-mono/LICENSE', 'uis/backoffice/assets/ibm-plex-mono.LICENSE');