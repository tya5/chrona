// Raster acceptance: use the same font engine as the exported preview, not estimates.
// NODE_PATH=$CODEX_PRIMARY_RUNTIME_NODE_MODULES node tools/verify-gantt-svg.cjs in.svg out.png
const fs = require('fs');
const sharp = require('sharp');

(async () => {
  const [input, output] = process.argv.slice(2);
  const svg = fs.readFileSync(input, 'utf8');
  const failures = [];
  let checked = 0;
  for (const match of svg.matchAll(/<text\b([^>]*)>([\s\S]*?)<\/text>/g)) {
    const attrs = Object.fromEntries([...match[1].matchAll(/([\w-]+)="([^"]*)"/g)].map(x => [x[1], x[2]]));
    if (!attrs['data-box-width']) continue;
    const fragment = `<svg xmlns="http://www.w3.org/2000/svg" width="2048" height="256"><text x="8" y="100" font-family="${attrs['font-family']}" font-size="${attrs['font-size']}" font-weight="${attrs['font-weight']}" fill="black">${match[2]}</text></svg>`;
    const { info } = await sharp(Buffer.from(fragment)).trim().png().toBuffer({resolveWithObject: true});
    const available = Number(attrs['data-box-width']);
    if (info.width > available) failures.push({text: match[2], actual: info.width, available});
    checked++;
  }
  if (failures.length) throw new Error(JSON.stringify(failures));
  await sharp(input).png().toFile(output);
  console.log(JSON.stringify({checkedTextLines: checked, overflows: failures.length, png: output}));
})().catch(error => { console.error(error); process.exitCode = 1; });
