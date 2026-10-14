const assert = require('node:assert/strict');
const { preparedCredentials } = require('/app/wildfire-backend/src/services/preparedNodeCredentials');

const nodes = preparedCredentials();
assert.equal(nodes.length, 10);
assert.equal(new Set(nodes.map((node) => node.node_id)).size, 10);
assert.equal(new Set(nodes.map((node) => node.key)).size, 10);
assert.equal(new Set(nodes.map((node) => node.generation)).size, 10);
console.log('Prepared FG1 credentials loaded: NODE01–NODE10, unique keys and generations');
