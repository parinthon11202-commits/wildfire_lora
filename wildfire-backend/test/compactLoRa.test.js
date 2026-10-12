const test = require('node:test');
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const { decodeCompactSensor, decryptUplink } = require('../src/services/secureLoRa');

// Independent .NET AES-GCM fixture, also used by firmware_checks/compact_radio.
const KEY = '00'.repeat(32);
const FRAME = 'RkdVMQEBAgMEBQYHCAAAAAAAAAABXhJe7QkFmBLnBGD0nkP+SLduZG26W3lrwSE=';
const PLAIN = Buffer.from('0100012c0aac1b750078', 'hex');

function signedPayload(plaintext) {
  const header = Buffer.from(FRAME, 'base64').subarray(0, 21);
  const nonce = Buffer.concat([header.subarray(0, 4), header.subarray(13)]);
  const cipher = crypto.createCipheriv('aes-256-gcm', Buffer.from(KEY, 'hex'), nonce);
  cipher.setAAD(header);
  return Buffer.concat([header, cipher.update(plaintext), cipher.final(), cipher.getAuthTag()]).toString('base64');
}

test('47-byte compact fixture decodes to the unchanged sensor API shape', () => {
  assert.equal(Buffer.from(FRAME, 'base64').length, 47);
  assert.equal(signedPayload(PLAIN), FRAME);
  const decoded = decryptUplink(FRAME, KEY);
  assert.equal(decoded.sequence, 1);
  assert.deepEqual(decoded.packet, {
    t: 's', id: 'NODE01', ri: 300, st: 'NORMAL', at: 27.32, h: 70.29, adc: 120
  });
});

test('every byte of the compact frame is authenticated', () => {
  const bytes = Buffer.from(FRAME, 'base64');
  for (let index = 0; index < bytes.length; index++) {
    const changed = Buffer.from(bytes);
    changed[index] ^= 1;
    assert.throws(() => decryptUplink(changed.toString('base64'), KEY), `byte ${index}`);
  }
});

test('negative temperature, missing readings and the node-selected state are preserved', () => {
  const fault = Buffer.from(PLAIN);
  fault[1] = 3;
  fault.writeInt16BE(-525, 4);
  fault.writeUInt16BE(65535, 6);
  fault.writeUInt16BE(65535, 8);
  assert.deepEqual(decodeCompactSensor(fault, 'NODE03'), {
    t: 's', id: 'NODE03', ri: 300, st: 'SENSOR_FAULT', at: -5.25, h: null, adc: null
  });
  fault.writeInt16BE(-32768, 4);
  assert.equal(decodeCompactSensor(fault, 'NODE03').at, null);
  const warning = Buffer.from(PLAIN);
  warning[1] = 2;
  warning.writeInt16BE(4500, 4); // Original raw value may be >45 before rounding.
  assert.equal(decodeCompactSensor(warning, 'NODE01').st, 'WARNING');
});

test('compact format rejects invalid sizes, states, intervals, ADC and non-fault sentinels', () => {
  for (const input of [PLAIN.subarray(0, 9), Buffer.concat([PLAIN, Buffer.from([0])])]) {
    assert.throws(() => decodeCompactSensor(input, 'NODE01'));
  }
  for (const change of [
    (b) => { b[0] = 9; }, (b) => { b[1] = 4; }, (b) => b.writeUInt16BE(0, 2),
    (b) => b.writeUInt16BE(4096, 8), (b) => b.writeInt16BE(-32768, 4),
    (b) => b.writeUInt16BE(65535, 6), (b) => b.writeUInt16BE(10001, 6),
    (b) => b.writeInt16BE(-2001, 4)
  ]) {
    const bytes = Buffer.from(PLAIN);
    change(bytes);
    assert.throws(() => decodeCompactSensor(bytes, 'NODE01'));
    assert.throws(() => decryptUplink(signedPayload(bytes), KEY));
  }
});
