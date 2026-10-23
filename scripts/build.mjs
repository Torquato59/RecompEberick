import { copyFile } from 'node:fs/promises';

for (const file of ['index.html', 'styles.css']) {
  await copyFile(new URL(`../frontend/${file}`, import.meta.url), new URL(`../dist/${file}`, import.meta.url));
}
console.log('Interface compilada em dist/.');
