// Local-only FG1 walkthrough: real MongoDB and backend code, simulated radio boards.
// This script connects only to the dedicated demo database on 127.0.0.1.
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const mongoose = require('mongoose');

const DEMO_DATABASE = 'wildfire_fg1_key_demo';
const DEMO_URI = `mongodb://127.0.0.1:27017/${DEMO_DATABASE}`;
const DEMO_MARKER = 'fg1-local-key-demo';
const NODE_ID = 'NODE01';

// Public, demo-only master key. Never use this value for a real deployment.
process.env.DEVICE_REGISTRY_KEY = '22'.repeat(32);
mongoose.set('autoCreate', false);
mongoose.set('autoIndex', false);

const NodeModel = require('../src/models/Node');
const Reading = require('../src/models/Reading');
const devicesRouter = require('../src/routes/devices');
const { handlePacket } = require('../src/services/packetHandler');
const { openDeviceKey, provisionProof } = require('../src/services/secureLoRa');

function routeHandler(method, path) {
  const layer = devicesRouter.stack.find((entry) =>
    entry.route?.path === path && entry.route.methods[method]);
  if (!layer) throw new Error(`Missing backend route: ${method.toUpperCase()} ${path}`);
  return layer.route.stack.at(-1).handle;
}

async function callBackendRoute(method, path, request = {}) {
  const response = {
    statusCode: 200,
    body: undefined,
    status(code) { this.statusCode = code; return this; },
    json(body) { this.body = body; return this; },
  };
  await routeHandler(method, path)(request, response, (error) => { throw error; });
  return response;
}

// Build the same FG1 frame layout the Node firmware sends, without a physical board.
function makeSensorFrame(key, generation, sequence) {
  const header = Buffer.alloc(21);
  header.write('FGU1', 0, 'ascii');
  header[4] = 1; // NODE01 occupies slot 1.
  Buffer.from(generation, 'hex').copy(header, 5);
  header.writeBigUInt64BE(BigInt(sequence), 13);
  const nonce = Buffer.concat([Buffer.from('FGU1'), header.subarray(13, 21)]);
  const cipher = crypto.createCipheriv('aes-256-gcm', Buffer.from(key, 'hex'), nonce);
  cipher.setAAD(header);
  const reading = Buffer.from(JSON.stringify({
    t: 's', id: NODE_ID, ri: 300, st: 'NORMAL', at: 28, h: 65, adc: 120,
  }));
  return Buffer.concat([
    header, cipher.update(reading), cipher.final(), cipher.getAuthTag(),
  ]).toString('base64');
}

async function expectRejected(label, frame, expectedStatus) {
  try {
    await handlePacket({ frame, rssi: -65, snr: 8 });
    throw new Error(`${label} was unexpectedly accepted`);
  } catch (error) {
    if (error.status !== expectedStatus) throw error;
    console.log(`${label}: rejected (${expectedStatus})`);
  }
}

async function main() {
  await mongoose.connect(DEMO_URI, { serverSelectionTimeoutMS: 5000 });
  try {
    const db = mongoose.connection.db;
    const marker = await db.collection('demo_meta').findOne({ _id: DEMO_MARKER });
    const collections = await db.listCollections().toArray();
    if (!marker && collections.length > 0) {
      throw new Error(`${DEMO_DATABASE} already has data but is not this demo; no changes made`);
    }
    if (!marker) await db.collection('demo_meta').insertOne({ _id: DEMO_MARKER, created_at: new Date() });

    let node = await NodeModel.findOne({ node_id: NODE_ID }).select('+credential_ciphertext +uplink_sequence');
    if (!node) {
      // Invoke the real backend registration and activation handlers.
      const registration = (await callBackendRoute('post', '/', { body: { slot: 1 } })).body;
      const proof = provisionProof(registration.key, NODE_ID, registration.generation, registration.challenge);
      await callBackendRoute('post', '/:node_id/activate', {
        params: { node_id: NODE_ID }, body: { generation: registration.generation, proof },
      });
      node = await NodeModel.findOne({ node_id: NODE_ID }).select('+credential_ciphertext +uplink_sequence');
      console.log('Registration: created and activated a demo NODE01');
    } else {
      assert.equal(node.registration_status, 'active', 'Existing demo NODE01 is not active');
      console.log('Registration: reused the existing demo NODE01 key');
    }

    const key = openDeviceKey(node.credential_ciphertext, NODE_ID, node.credential_generation);
    const gatewayReply = (await callBackendRoute('get', '/gateway')).body;
    const gatewayNode = gatewayReply.devices.find((item) => item.node_id === NODE_ID);
    assert.equal(gatewayNode?.key, key);

    const stored = await db.collection('nodes').findOne({ node_id: NODE_ID });
    assert.notEqual(stored.credential_ciphertext, key);
    const before = await Reading.countDocuments({ node_id: NODE_ID });
    const sequence = node.uplink_sequence + 1;
    const frame = makeSensorFrame(key, node.credential_generation, sequence);
    const accepted = await handlePacket({ frame, rssi: -65, snr: 8 });
    assert.equal(accepted.type, 'sensor');
    assert.equal(await Reading.countDocuments({ node_id: NODE_ID }), before + 1);

    const wrongKey = crypto.randomBytes(32).toString('hex');
    await expectRejected('Wrong key', makeSensorFrame(wrongKey, node.credential_generation, sequence + 1), 401);
    await expectRejected('Repeated packet', frame, 409);
    const after = await Reading.countDocuments({ node_id: NODE_ID });
    assert.equal(after, before + 1);

    console.log(`MongoDB: ${DEMO_URI}`);
    console.log(`Demo NODE01 key (not a real device key): ${key}`);
    console.log(`Stored nodes.credential_ciphertext: ${stored.credential_ciphertext}`);
    console.log('Gateway received the matching key from the backend: yes');
    console.log(`Correct key: accepted; readings for NODE01: ${before} -> ${after}`);
    console.log('Wrong key and repeated packet added no readings.');
    console.log('Open MongoDB Compass > wildfire_fg1_key_demo > nodes / readings to inspect.');
  } finally {
    await mongoose.disconnect();
  }
}

main().catch((error) => {
  console.error(`FG1 local demo failed: ${error.message}`);
  process.exitCode = 1;
});
