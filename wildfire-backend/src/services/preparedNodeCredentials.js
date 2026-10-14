const fs = require('node:fs');
const path = require('node:path');
const { failure, nodeIdForSlot } = require('./secureLoRa');

const DEFAULT_FILE = path.resolve(__dirname, '../../node-credentials.local.json');

function credentialsFile() {
  return path.resolve(process.env.NODE_CREDENTIALS_FILE || DEFAULT_FILE);
}

function preparedCredentials() {
  let document;
  try {
    document = JSON.parse(fs.readFileSync(credentialsFile(), 'utf8'));
  } catch {
    throw failure('ยังไม่มีไฟล์กุญแจ NODE01–NODE10 สำหรับลงทะเบียน', 503);
  }
  if (document?.protocol !== 'FG1' || !Array.isArray(document.nodes) || document.nodes.length !== 10) {
    throw failure('ไฟล์กุญแจโหนดไม่ครบหรือรูปแบบไม่ถูกต้อง', 503);
  }
  const keys = new Set();
  const generations = new Set();
  for (let index = 0; index < 10; index++) {
    const item = document.nodes[index];
    if (item?.node_id !== nodeIdForSlot(index + 1) ||
        !/^[0-9a-f]{64}$/.test(item.key || '') ||
        !/^[0-9a-f]{16}$/.test(item.generation || '') ||
        keys.has(item.key) || generations.has(item.generation)) {
      throw failure('ไฟล์กุญแจโหนดไม่ครบหรือรูปแบบไม่ถูกต้อง', 503);
    }
    keys.add(item.key);
    generations.add(item.generation);
  }
  return document.nodes;
}

function preparedCredentialForSlot(slot) {
  return preparedCredentials()[slot - 1];
}

module.exports = { credentialsFile, preparedCredentials, preparedCredentialForSlot };
