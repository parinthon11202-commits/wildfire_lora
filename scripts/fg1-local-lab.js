// Local-only FG1 lab. Real Backend/MongoDB/API, simulated Node and Gateway radio.
// Run via start-fg1-local.ps1 so the dashboard is built before the backend starts.
const crypto = require('node:crypto');
const fs = require('node:fs');
const http = require('node:http');
const path = require('node:path');
const { spawn } = require('node:child_process');
const { createRequire } = require('node:module');

const root = path.resolve(__dirname, '..');
const backendDir = path.join(root, 'wildfire-backend');
const backendRequire = createRequire(path.join(backendDir, 'package.json'));
const mongoose = backendRequire('mongoose');
const { decryptUplink, provisionProof } = require('../wildfire-backend/src/services/secureLoRa');
const labDir = path.join(root, '.fg1-local');
const configPath = path.join(labDir, 'config.json');
const credentialsPath = path.join(labDir, 'node-credentials.json');
const nodePath = path.join(labDir, 'node01.json');
const databaseUri = 'mongodb://127.0.0.1:27017/wildfire_fg1_local_lab';
const backendUrl = 'http://127.0.0.1:4400';
const labUrl = 'http://127.0.0.1:4401';
const nodeId = 'NODE01';
const events = [];
let backend;
let labServer;
let stopping = false;
let node;
let lastFrame;
let currentState = 'NORMAL';
let queue = Promise.resolve();
let heartbeatTimer;
let sensorTimer;

function event(message) {
  const line = `${new Date().toLocaleTimeString('th-TH', { timeZone: 'Asia/Bangkok' })} ${message}`;
  events.unshift(line);
  events.length = Math.min(events.length, 18);
  console.log(line);
}

function saveJson(file, value) {
  const temporary = `${file}.tmp`;
  fs.writeFileSync(temporary, `${JSON.stringify(value, null, 2)}\n`, { mode: 0o600 });
  fs.renameSync(temporary, file);
}

function configuration() {
  fs.mkdirSync(labDir, { recursive: true });
  if (!fs.existsSync(configPath)) {
    saveJson(configPath, {
      databaseUri,
      registryKey: crypto.randomBytes(32).toString('hex'),
      gatewayKey: crypto.randomBytes(32).toString('hex'),
      createdAt: new Date().toISOString(),
    });
  }
  if (!fs.existsSync(credentialsPath)) {
    saveJson(credentialsPath, {
      protocol: 'FG1',
      nodes: Array.from({ length: 10 }, (_, index) => ({
        node_id: `NODE${String(index + 1).padStart(2, '0')}`,
        generation: crypto.randomBytes(8).toString('hex'),
        key: crypto.randomBytes(32).toString('hex'),
      })),
    });
  }
  const config = JSON.parse(fs.readFileSync(configPath, 'utf8'));
  if (config.databaseUri !== databaseUri ||
      !/^[0-9a-f]{64}$/.test(config.registryKey) ||
      !/^[0-9a-f]{64}$/.test(config.gatewayKey)) {
    throw new Error('Local lab configuration is invalid; check .fg1-local/config.json');
  }
  return config;
}

async function request(pathname, options = {}) {
  const response = await fetch(`${backendUrl}${pathname}`, {
    method: options.method || 'GET',
    headers: {
      Accept: 'application/json',
      ...(options.body === undefined ? {} : { 'Content-Type': 'application/json' }),
      ...(options.gatewayKey ? { 'x-gateway-key': options.gatewayKey } : {}),
    },
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
    signal: AbortSignal.timeout(5000),
  });
  const body = await response.json().catch(() => ({}));
  return { status: response.status, body };
}

function expectStatus(result, status, label) {
  if (result.status !== status) {
    throw new Error(`${label}: HTTP ${result.status} ${result.body.error || ''}`.trim());
  }
  return result.body;
}

async function waitForBackend() {
  for (let attempt = 0; attempt < 40; attempt += 1) {
    if (backend.exitCode !== null) throw new Error('Backend stopped during startup');
    try {
      const health = await request('/api/health');
      if (health.status === 200 && health.body.local_lab && health.body.mongo_state === 1) return;
    } catch { /* Wait while Backend connects to local MongoDB. */ }
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  throw new Error('Backend did not become ready on 127.0.0.1:4400');
}

async function gatewayDevice(config) {
  const reply = expectStatus(await request('/api/devices/gateway', {
    gatewayKey: config.gatewayKey,
  }), 200, 'Gateway key sync');
  return reply.devices.find((device) => device.node_id === nodeId);
}

async function provision(config) {
  const list = expectStatus(await request('/api/devices'), 200, 'List devices');
  const existing = list.find((item) => item.node_id === nodeId);
  if (fs.existsSync(nodePath)) {
    node = JSON.parse(fs.readFileSync(nodePath, 'utf8'));
    const gateway = await gatewayDevice(config);
    if (!gateway || gateway.generation !== node.generation || gateway.key !== node.key) {
      throw new Error('Saved simulated Node key does not match Backend; do not overwrite it automatically');
    }
    if (node.sequence < gateway.last_sequence) {
      node.sequence = gateway.last_sequence;
      saveJson(nodePath, node);
    }
    event('โหลดกุญแจ NODE01 เดิมจากไฟล์โหนดจำลอง');
    return;
  }
  if (existing?.status === 'active') {
    throw new Error('NODE01 is active but the simulated Node key file is missing');
  }
  const registration = expectStatus(await request('/api/devices', {
    method: 'POST', body: { slot: 1, ...(existing ? { replace: true } : {}) },
  }), 201, 'Register NODE01');
  const proof = provisionProof(registration.key, nodeId, registration.generation, registration.challenge);
  expectStatus(await request(`/api/devices/${nodeId}/activate`, {
    method: 'POST', body: { generation: registration.generation, proof },
  }), 200, 'Activate NODE01');
  node = {
    simulated: true, node_id: nodeId, generation: registration.generation,
    key: registration.key, sequence: 0,
  };
  saveJson(nodePath, node);
  const gateway = await gatewayDevice(config);
  if (!gateway || gateway.key !== node.key) throw new Error('Gateway received a different NODE01 key');
  event('ลงทะเบียน NODE01 ผ่าน Backend จริง; MongoDB เก็บ credential_ciphertext');
}

function makeFrame(key, generation, sequence, payload) {
  const header = Buffer.alloc(21);
  header.write('FGU1', 0, 'ascii');
  header[4] = 1;
  Buffer.from(generation, 'hex').copy(header, 5);
  header.writeBigUInt64BE(BigInt(sequence), 13);
  const nonce = Buffer.concat([Buffer.from('FGU1'), header.subarray(13, 21)]);
  const cipher = crypto.createCipheriv('aes-256-gcm', Buffer.from(key, 'hex'), nonce);
  cipher.setAAD(header);
  const plaintext = Buffer.from(JSON.stringify(payload));
  return Buffer.concat([header, cipher.update(plaintext), cipher.final(), cipher.getAuthTag()])
    .toString('base64');
}

async function send(config, type, state = currentState) {
  const gateway = await gatewayDevice(config);
  if (!gateway || gateway.key !== node.key || gateway.generation !== node.generation) {
    throw new Error('Gateway does not have the current NODE01 key');
  }
  node.sequence += 1;
  saveJson(nodePath, node); // Reserve before sending so a restart cannot reuse this nonce.
  const values = {
    NORMAL: { at: 28, h: 65, adc: 120 },
    WATCH: { at: 37, h: 42, adc: 310 },
    WARNING: { at: 48, h: 25, adc: 700 },
  };
  const payload = type === 'gps'
    ? { t: 'gps', id: nodeId, gf: 1, la: 18.7883, ln: 98.9853 }
    : { t: 's', id: nodeId, ri: 15, st: state, ...values[state] };
  const frame = makeFrame(node.key, node.generation, node.sequence, payload);
  const checked = decryptUplink(frame, gateway.key); // Simulated Gateway radio check.
  if (checked.nodeId !== nodeId || checked.sequence !== node.sequence) {
    throw new Error('Gateway frame check failed');
  }
  const result = expectStatus(await request('/api/packets', {
    method: 'POST', gatewayKey: config.gatewayKey,
    body: { frame, rssi: -65, snr: 8 },
  }), 201, 'Backend packet');
  lastFrame = frame;
  event(`NODE01 → Gateway → Backend → MongoDB: ${type === 'gps' ? 'GPS' : state} (#${node.sequence})`);
  return result;
}

function enqueue(action) {
  const result = queue.then(action);
  queue = result.catch(() => undefined);
  return result;
}

async function wrongKey(config) {
  const readingsBefore = await mongoose.connection.db.collection('readings').countDocuments({ node_id: nodeId });
  const gateway = await gatewayDevice(config);
  node.sequence += 1;
  saveJson(nodePath, node);
  const frame = makeFrame(crypto.randomBytes(32).toString('hex'), node.generation, node.sequence,
    { t: 's', id: nodeId, ri: 15, st: 'NORMAL', at: 28, h: 65, adc: 120 });
  let gatewayRejected = false;
  try { decryptUplink(frame, gateway.key); } catch { gatewayRejected = true; }
  if (!gatewayRejected) throw new Error('Gateway unexpectedly accepted a wrong key');
  // Deliberately bypass the simulated Gateway once to show Backend's independent check.
  const backendResult = await request('/api/packets', {
    method: 'POST', gatewayKey: config.gatewayKey, body: { frame, rssi: -65, snr: 8 },
  });
  if (backendResult.status !== 401) throw new Error(`Expected Backend 401, got ${backendResult.status}`);
  const readingsAfter = await mongoose.connection.db.collection('readings').countDocuments({ node_id: nodeId });
  if (readingsAfter !== readingsBefore) throw new Error('Wrong key unexpectedly created a reading');
  event(`กุญแจผิด: Gateway ปฏิเสธ; เมื่อลองส่งตรง Backend ก็ปฏิเสธ HTTP 401`);
  return { gatewayRejected, backendStatus: backendResult.status };
}

async function replay(config) {
  if (!lastFrame) throw new Error('Send one valid packet first');
  const readingsBefore = await mongoose.connection.db.collection('readings').countDocuments({ node_id: nodeId });
  const result = await request('/api/packets', {
    method: 'POST', gatewayKey: config.gatewayKey,
    body: { frame: lastFrame, rssi: -65, snr: 8 },
  });
  if (result.status !== 409) throw new Error(`Expected Backend 409, got ${result.status}`);
  const readingsAfter = await mongoose.connection.db.collection('readings').countDocuments({ node_id: nodeId });
  if (readingsAfter !== readingsBefore) throw new Error('Replay unexpectedly created a reading');
  event('ส่งแพ็กเก็ตเดิมซ้ำ: Backend ปฏิเสธ HTTP 409; readings ไม่เพิ่ม');
  return { backendStatus: result.status };
}

async function status() {
  const db = mongoose.connection.db;
  const stored = await db.collection('nodes').findOne({ node_id: nodeId });
  const readingCount = await db.collection('readings').countDocuments({ node_id: nodeId });
  const alertCount = await db.collection('alerts').countDocuments({ node_id: nodeId });
  const activeAlertCount = await db.collection('alerts').countDocuments({ node_id: nodeId, active: true });
  const latest = await db.collection('readings').find({ node_id: nodeId })
    .sort({ timestamp: -1 }).limit(1).next();
  const health = expectStatus(await request('/api/health'), 200, 'Backend health');
  return {
    database: 'wildfire_fg1_local_lab',
    backend: health.ok, gatewayConnected: health.gateway.connected,
    nodeStatus: stored?.registration_status,
    generation: node.generation, nodeKey: node.key,
    ciphertext: stored?.credential_ciphertext,
    sequence: stored?.uplink_sequence,
    readingCount, alertCount, activeAlertCount, latest: latest && {
      state: latest.state, air_temp: latest.air_temp, humidity: latest.humidity,
      particle_adc: latest.particle_adc, timestamp: latest.timestamp,
    },
    currentState, events,
  };
}

const page = `<!doctype html>
<html lang="th"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>FG1 Local Lab</title><style>
body{font-family:system-ui,sans-serif;background:#f4f6f2;color:#18362f;margin:0;padding:24px}
main{max-width:1050px;margin:auto}h1{margin-bottom:4px}p{line-height:1.55}
.intro{background:#fff4d9;border:1px solid #e9c96e;padding:14px 18px;border-radius:14px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(290px,1fr));gap:14px;margin:16px 0}
.card{background:#fff;border:1px solid #dce7de;border-radius:14px;padding:18px;min-width:0}
button{border:0;background:#166c54;color:white;border-radius:9px;padding:10px 14px;margin:4px;cursor:pointer;font-weight:700}
button.alt{background:#9a571e}button:hover{filter:brightness(.92)}
code{overflow-wrap:anywhere;background:#eef3ee;padding:3px 5px;border-radius:5px}
.secret{font-family:monospace;word-break:break-all}a{color:#146b56}li{margin:5px 0}
</style><main>
<h1>FG1 · ทดลองบนเครื่อง</h1>
<p class="intro">Backend, MongoDB และ API ทำงานจริงบนเครื่องนี้ ส่วนโหนดกับ Gateway เป็นโปรแกรมจำลอง ไม่มีการส่งคลื่น LoRa หรือใช้บอร์ดจริง และไม่มีการ deploy</p>
<p><a href="http://127.0.0.1:4400" target="_blank" rel="noopener">เปิด Dashboard</a> · MongoDB Compass → 127.0.0.1:27017 → <code>wildfire_fg1_local_lab</code></p>
<div class="grid">
<section class="card"><h2>สถานะ</h2><p id="health">กำลังโหลด…</p><p id="count"></p><p id="latest"></p></section>
<section class="card"><h2>ลองส่งข้อมูล</h2><p>ค่าที่เลือกจะส่งต่อทุก 15 วินาทีจนกว่าจะเลือกใหม่</p>
<button data-action="NORMAL">ปกติ</button><button data-action="WATCH">เฝ้าระวัง</button><button data-action="WARNING">เตือนภัย</button>
<button data-action="gps">ส่งพิกัด</button><p id="action-result"></p></section>
<section class="card"><h2>ลองความปลอดภัย</h2>
<button class="alt" data-action="wrong">ส่งด้วยกุญแจผิด</button>
<button class="alt" data-action="replay">ส่งข้อมูลเดิมซ้ำ</button>
<p>Gateway และ Backend จะปฏิเสธข้อมูลที่ตรวจไม่ผ่าน</p></section>
<section class="card"><h2>กุญแจ NODE01</h2>
<p>กุญแจจริงของ <strong>โหนดจำลอง</strong> อยู่ใน <code>.fg1-local/node01.json</code>:</p>
<button id="reveal" type="button">แสดง/ซ่อนกุญแจ</button><p id="key" class="secret" hidden></p>
<p>ใน MongoDB → <code>nodes.credential_ciphertext</code> เก็บเป็นค่าที่เข้ารหัสแล้ว:</p>
<p id="ciphertext" class="secret"></p><p id="generation"></p></section>
</div><section class="card"><h2>สิ่งที่เกิดขึ้น</h2><ol id="events"></ol></section>
<p>ข้อมูลในฐานนี้แยกจาก <code>wildfire_lora</code> และ <code>wildfire_lora_local</code> · ปิดโปรแกรมด้วย Ctrl+C ใน PowerShell</p>
</main><script>
async function refresh(){
 try{const r=await fetch('/api/status');const x=await r.json();if(!r.ok)throw Error(x.error);
 document.getElementById('health').textContent='Backend '+(x.backend?'พร้อม':'ไม่พร้อม')+' · Gateway จำลอง '+(x.gatewayConnected?'เชื่อมต่อ':'ไม่เชื่อมต่อ')+' · NODE01 '+x.nodeStatus;
 document.getElementById('count').textContent='ข้อมูลที่รับแล้ว '+x.readingCount+' ครั้ง · เหตุการณ์ '+x.alertCount+' (กำลังเกิด '+x.activeAlertCount+') · ลำดับแพ็กเก็ต '+x.sequence+' · โหมด '+x.currentState;
 document.getElementById('latest').textContent=x.latest?'ล่าสุด '+x.latest.state+' · '+x.latest.air_temp+'°C · ความชื้น '+x.latest.humidity+'% · ADC '+x.latest.particle_adc:'ยังไม่มีข้อมูล';
 document.getElementById('key').textContent=x.nodeKey;
 document.getElementById('ciphertext').textContent=x.ciphertext||'ยังไม่มี';
 document.getElementById('generation').textContent='รุ่นกุญแจ: '+x.generation;
 document.getElementById('events').replaceChildren(...x.events.map(s=>{const li=document.createElement('li');li.textContent=s;return li}));
 }catch(e){document.getElementById('health').textContent=String(e)}}
for(const button of document.querySelectorAll('[data-action]'))button.addEventListener('click',async()=>{
 const result=document.getElementById('action-result');result.textContent='กำลังส่ง…';
 try{const r=await fetch('/api/action',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({type:button.dataset.action})});
 const x=await r.json();if(!r.ok)throw Error(x.error);result.textContent='สำเร็จ: '+button.textContent;await refresh()}
 catch(e){result.textContent='ผิดพลาด: '+String(e)}});
document.getElementById('reveal').addEventListener('click',()=>{const e=document.getElementById('key');e.hidden=!e.hidden});
refresh();setInterval(refresh,3000);
</script></html>`;

function sendJson(response, code, value) {
  response.writeHead(code, { 'Content-Type': 'application/json; charset=utf-8',
    'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff' });
  response.end(JSON.stringify(value));
}

function startLabServer(config) {
  labServer = http.createServer(async (req, res) => {
    if (req.headers.host !== '127.0.0.1:4401') {
      return sendJson(res, 403, { error: 'Use 127.0.0.1:4401' });
    }
    if (req.method === 'GET' && req.url === '/') {
      res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8',
        'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff' });
      return res.end(page);
    }
    try {
      if (req.method === 'GET' && req.url === '/api/status') {
        return sendJson(res, 200, await status());
      }
      if (req.method === 'POST' && req.url === '/api/action') {
        if (req.headers.origin !== labUrl ||
            !String(req.headers['content-type'] || '').startsWith('application/json')) {
          return sendJson(res, 403, { error: 'Local lab origin required' });
        }
        let raw = '';
        for await (const chunk of req) {
          raw += chunk;
          if (raw.length > 1000) throw new Error('Request too large');
        }
        const { type } = JSON.parse(raw);
        const result = await enqueue(async () => {
          if (['NORMAL', 'WATCH', 'WARNING'].includes(type)) {
            currentState = type;
            return send(config, 'sensor', type);
          }
          if (type === 'gps') return send(config, 'gps');
          if (type === 'wrong') return wrongKey(config);
          if (type === 'replay') return replay(config);
          throw new Error('Unknown action');
        });
        return sendJson(res, 200, result);
      }
      return sendJson(res, 404, { error: 'Not found' });
    } catch (error) {
      event(`ผิดพลาด: ${error.message}`);
      return sendJson(res, 400, { error: error.message });
    }
  });
  return new Promise((resolve, reject) => {
    labServer.once('error', reject);
    labServer.listen(4401, '127.0.0.1', resolve);
  });
}

function stop() {
  if (stopping) return;
  stopping = true;
  clearInterval(heartbeatTimer);
  clearInterval(sensorTimer);
  labServer?.close();
  backend?.kill();
  mongoose.disconnect().finally(() => process.exit(0));
}

async function main() {
  if (!fs.existsSync(path.join(root, 'wildfire-dashboard', 'dist', 'index.html'))) {
    throw new Error('Dashboard build is missing; run start-fg1-local.ps1');
  }
  const config = configuration();
  process.env.DEVICE_REGISTRY_KEY = config.registryKey;
  process.env.NODE_CREDENTIALS_FILE = credentialsPath;
  backend = spawn(process.execPath, ['src/server.js'], {
    cwd: backendDir, windowsHide: true, stdio: 'inherit',
    env: { ...process.env, PORT: '4400', MONGODB_URI: databaseUri,
      DEVICE_REGISTRY_KEY: config.registryKey, GATEWAY_API_KEY: config.gatewayKey,
      NODE_CREDENTIALS_FILE: credentialsPath,
      CORS_ORIGINS: `${backendUrl},${labUrl}`,
      FG1_LOCAL_LAB: '1', TELEGRAM_BOT_TOKEN: '', TELEGRAM_CHAT_ID: '' },
  });
  backend.on('exit', (code) => {
    if (!stopping) {
      console.error(`Local Backend stopped (${code}); closing lab`);
      process.exit(1);
    }
  });
  await waitForBackend();
  await mongoose.connect(databaseUri, { serverSelectionTimeoutMS: 5000 });
  await provision(config);
  await enqueue(async () => {
    await send(config, 'sensor');
    const stored = await mongoose.connection.db.collection('nodes').findOne({ node_id: nodeId });
    if (!stored?.gps_fixed) await send(config, 'gps');
  });
  await startLabServer(config);
  heartbeatTimer = setInterval(() => gatewayDevice(config).catch((error) => event(`Gateway sync: ${error.message}`)), 8000);
  sensorTimer = setInterval(() => enqueue(() => send(config, 'sensor'))
    .catch((error) => event(`ส่งข้อมูลไม่สำเร็จ: ${error.message}`)), 15000);
  event(`เปิด ${labUrl} และ Dashboard ${backendUrl}`);
  console.log('Press Ctrl+C to stop this local lab.');
}

process.on('SIGINT', stop);
process.on('SIGTERM', stop);
main().catch(async (error) => {
  console.error(`FG1 local lab failed: ${error.message}`);
  stopping = true;
  backend?.kill();
  await mongoose.disconnect().catch(() => undefined);
  process.exitCode = 1;
});
