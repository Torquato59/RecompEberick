import { copyFile } from 'node:fs/promises';
import { build } from 'esbuild';

await build({
  entryPoints: [new URL('../frontend/app.ts', import.meta.url).pathname],
  outfile: new URL('../dist/app.js', import.meta.url).pathname,
  bundle: true,
  format: 'esm',
  target: 'es2022',
  minify: true,
  legalComments: 'inline',
});

for (const file of ['index.html', 'styles.css']) {
  await copyFile(new URL(`../frontend/${file}`, import.meta.url), new URL(`../dist/${file}`, import.meta.url));
}
console.log('Interface compilada em dist/.');
