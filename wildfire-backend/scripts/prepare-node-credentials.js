// Create the private, human-readable credential sheet before provisioning boards.
const crypto = require('node:crypto');
const fs = require('node:fs');
const { credentialsFile, preparedCredentials } = require('../src/services/preparedNodeCredentials');

const file = credentialsFile();
const rotation = process.argv[2];
const makeEntry = (nodeId) => ({
  node_id: nodeId,
  generation: crypto.randomBytes(8).toString('hex'),
  key: crypto.randomBytes(32).toString('hex')
});

if (rotation && (!/^NODE(0[1-9]|10)$/.test(rotation) || process.argv.length !== 3)) {
  throw new Error('Usage: node scripts/prepare-node-credentials.js [NODE01–NODE10]');
}

if (rotation) {
  const nodes = preparedCredentials().map((item) => item.node_id === rotation ? makeEntry(rotation) : item);
  const temporary = `${file}.${process.pid}.tmp`;
  try {
    fs.writeFileSync(temporary, `${JSON.stringify({ protocol: 'FG1', nodes }, null, 2)}\n`,
      { flag: 'wx', mode: 0o600 });
    fs.renameSync(temporary, file);
  } finally {
    if (fs.existsSync(temporary)) fs.unlinkSync(temporary);
  }
  console.log(`Prepared a new unused credential for ${rotation} in ${file}. Restart the backend before provisioning.`);
} else {
  const nodes = Array.from({ length: 10 }, (_, index) => makeEntry(`NODE${String(index + 1).padStart(2, '0')}`));
  fs.writeFileSync(file, `${JSON.stringify({ protocol: 'FG1', nodes }, null, 2)}\n`,
    { flag: 'wx', mode: 0o600 });
  console.log(`Prepared NODE01–NODE10 credentials in ${file}. Values were not printed.`);
}
