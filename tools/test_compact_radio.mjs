// Actual C++ codec, timing, retry loop and Gateway queue/reply path with mocks.
// Crypto is checked separately by backend fixtures and the ESP32 self-check sketch.
import assert from 'node:assert/strict'
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { compileWasm } from './compile_wasm.mjs'

const root = resolve(import.meta.dirname, '..')
const output = resolve(root, '.codex-build/compact-radio-tests')
const compiler = process.env.CLANGXX || 'C:/Users/14tha/AppData/Local/Android/Sdk/ndk/28.2.13676358/toolchains/llvm/prebuilt/windows-x86_64/bin/clang++.exe'
mkdirSync(output, { recursive: true })
const read = (path) => readFileSync(resolve(root, path), 'utf8')
const header = (path) => read(path).replace(/^#(?:pragma|include).*$/gm, '')
function extract(path, name) {
  const match = read(path).match(new RegExp('^(?:bool|uint32_t|void) ' + name + '\\([^]*?^}', 'm'))
  assert.ok(match, name)
  return match[0]
}
const prelude = `
typedef unsigned char uint8_t;
typedef short int16_t;
typedef unsigned short uint16_t;
typedef int int32_t;
typedef unsigned int uint32_t;
typedef unsigned long long uint64_t;
typedef unsigned int size_t;
#define INT16_MIN (-32768)
#define INT16_MAX 32767
#define UINT16_MAX 65535
#define UINT32_MAX 4294967295U
bool isfinite(float n) { return __builtin_isfinite(n); }
long lroundf(float n) { return (long)(n < 0 ? n - 0.5f : n + 0.5f); }
extern "C" void* memcpy(void* out, const void* in, size_t count) {
  for (size_t i=0;i<count;i++) ((uint8_t*)out)[i]=((const uint8_t*)in)[i]; return out;
}
extern "C" void* memset(void* out, int n, size_t count) {
  for (size_t i=0;i<count;i++) ((uint8_t*)out)[i]=n; return out;
}
extern "C" int memcmp(const void* a, const void* b, size_t count) {
  for (size_t i=0;i<count;i++) if (((const uint8_t*)a)[i] != ((const uint8_t*)b)[i])
    return ((const uint8_t*)a)[i] - ((const uint8_t*)b)[i]; return 0;
}
extern "C" void* memchr(const void* p,int n,size_t count) {
  for(size_t i=0;i<count;i++)if(((const uint8_t*)p)[i]==n)return (void*)((const uint8_t*)p+i);
  return 0;
}
template<typename T> T min(T a, T b) { return a < b ? a : b; }
bool equal(const char* a,const char* b) { while (*a && *a==*b) {a++;b++;} return *a==*b; }
struct String {
  const char* text; String(const char* s=""):text(s) {}
  size_t length() const { size_t n=0;while(text[n])n++;return n; }
  const char* c_str() const { return text; }
  bool operator==(const String& b) const { return equal(text,b.text); }
  bool operator!=(const String& b) const { return !(*this==b); }
  String operator+(unsigned slot) const { return slot==1?String("slot1"):String("other-slot"); }
};
struct Console { template<typename T> void print(T) {} template<typename T> void println(T) {} } Serial;
unsigned nowMs, originMs;
unsigned long millis() { return nowMs; }
void delay(unsigned duration) { nowMs += duration; }
constexpr size_t FG_HEADER=21, FG_TAG=16, FG_MAX_FRAME=255;
${header('radio_common/compact_packets.h')}
${header('radio_common/radio_timing.h')}
${header('radio_common/reply_cache.h')}
`
const nodeCpp = prelude + `
#define SECURE_LORA_ENABLED 1
#define NODE_ID "NODE01"
#include "${resolve(root, 'sensor_common/sensor_config.h').replaceAll('\\', '/')}"
enum FireStatus {NORMAL,WATCH,WARNING,SENSOR_FAULT};
struct SensorData {float airTemp;float humidity;int particleAdc;};
${extract('sensor_common/risk_rules.h', 'plannedReportIntervalSeconds')}
uint32_t radioCycleStartedMs, radioCycleBudgetMs;
bool radioDeadlineLogged, radioReady=true;
int scenario, randomCalls, prepareCalls, txCalls, sleeps, rxCalls, frameMismatch;
unsigned randomCaps[3], delays[3]; uint8_t firstFrame[255];
long random(long, long maximum) {
  const unsigned cap=maximum-1; randomCaps[randomCalls]=cap;
  const unsigned value=scenario==3?cap:scenario==5?(randomCalls+1)*100:0;
  delays[randomCalls++]=value; return value;
}
struct Radio { void sleep() {sleeps++;} } LoRa;
bool ensureLoRaReady() { return radioReady; }
size_t prepareSecurePayload(const uint8_t* p,size_t n,uint8_t* frame) {
  prepareCalls++; memset(frame,0,47);memcpy(frame+21,p,n);frame[20]=prepareCalls;return 47;
}
bool transmitPreparedSecureFrame(const uint8_t* p,size_t n) {
  if (!txCalls) memcpy(firstFrame,p,n); else if(memcmp(firstFrame,p,n))frameMismatch++;
  txCalls++; nowMs+=fgTimeOnAirMs(n,10,125000); return scenario!=6;
}
bool listenForGatewayCommand(bool) {
  rxCalls++; const bool ack=scenario==1 || (scenario==2 && txCalls==2);
  nowMs += ack?535:6000; return ack;
}
${['remainingRadioCycleMs','radioExchangeCostMs','waitForRadioTurn','sendCompactMeasurement'].map(n=>extract('sensor_common/lora_transport.h',n)).join('\n')}
extern "C" int run(int which,int warning,int wrap) {
  scenario=which;nowMs=originMs=wrap?4294967000U:0;
  radioCycleStartedMs=nowMs;radioCycleBudgetMs=plannedReportIntervalSeconds(warning?WARNING:NORMAL)*1000;radioDeadlineLogged=false;
  randomCalls=prepareCalls=txCalls=sleeps=rxCalls=frameMismatch=0;
  radioReady=which!=7;
  const SensorData data={27.32273f,70.28854f,120};
  return sendCompactMeasurement(data,warning?WARNING:NORMAL);
}
extern "C" unsigned elapsed() {return nowMs-originMs;}
extern "C" int attempts() {return txCalls;}
extern "C" int preparations() {return prepareCalls;}
extern "C" int mismatch() {return frameMismatch;}
extern "C" int randoms() {return randomCalls;}
extern "C" int receivers() {return rxCalls;}
extern "C" unsigned cap(int i) {return randomCaps[i];}
extern "C" unsigned jitter(int i) {return delays[i];}
extern "C" unsigned interval(int state) {return plannedReportIntervalSeconds((FireStatus)state);}
extern "C" unsigned transmittedInterval() {return fgReadU16(firstFrame+FG_HEADER+2);}
extern "C" int codec(float t,float h,int adc,int fault) {
  uint8_t bytes[10];FgSensorValues decoded;
  if(!fgEncodeSensor(bytes,fault?3:0,300,t,h,adc))return -1;
  if(!fgDecodeSensor(bytes,10,decoded))return -2;
  return decoded.temperature100;
}
extern "C" int humidity(float h) {
  uint8_t bytes[10];fgEncodeSensor(bytes,3,300,27,h,0);return fgReadU16(bytes+6);
}
extern "C" int toa(int length,int sf,int crc) {return fgTimeOnAirMs(length,sf,125000,crc);}
extern "C" int cache(int scenario) {
  FgReplyCache cached;uint8_t request[47]={1};
  fgRememberRequest(cached,request,47,4294967000U);
  if(scenario==1)request[46]^=1;
  return fgCachedRequestMatches(cached,request,47,scenario==2?4294967000U+60000U:500U);
}
`
async function compile(name, cpp) {
  const input=resolve(output,name+'.cpp'), binary=resolve(output,name+'.wasm')
  writeFileSync(input,cpp)
  compileWasm(compiler,input,binary)
  return (await WebAssembly.instantiate(readFileSync(binary))).instance.exports
}
const node = await compile('node',nodeCpp)
assert.deepEqual([0,1,2,3].map(state=>node.interval(state)),[60,40,20,60])
assert.equal(node.codec(27.32273,70.28854,120,0),2732)
assert.equal(node.humidity(70.28854),7029)
assert.equal(node.codec(-5.255,70,120,0),-526)
assert.equal(node.codec(NaN,NaN,-1,1),-32768)
assert.equal(node.humidity(NaN),65535)
assert.equal(node.codec(NaN,70,120,0),-1)
assert.equal(node.codec(86,70,120,0),-2)
assert.equal(node.toa(47,10,0),576); assert.equal(node.toa(40,10,1),535)
assert.equal(node.cache(0),1,'Cache survives millis wrap')
assert.equal(node.cache(1),0,'Changed bytes are not a permitted retry')
assert.equal(node.cache(2),0,'Expired cache is not a permitted retry')
assert.equal(node.run(1,1,0),1); assert.equal(node.attempts(),1); assert.equal(node.elapsed(),1111)
assert.equal(node.transmittedInterval(),20,'WARNING interval is carried in the sensor payload')
assert.equal(node.run(2,1,0),1); assert.equal(node.attempts(),2)
assert.equal(node.preparations(),1); assert.equal(node.mismatch(),0)
assert.equal(node.run(0,0,0),0); assert.equal(node.attempts(),3,'Max three total attempts')
assert.equal(node.transmittedInterval(),60,'New NORMAL interval is carried in the sensor payload')
assert.equal(node.randoms(),3); assert.equal(node.preparations(),1); assert.equal(node.mismatch(),0)
assert.equal(node.cap(0),10000); assert.equal(node.cap(1),3000)
assert.equal(node.run(0,1,0),0); assert.equal(node.attempts(),2,'WARNING budget forbids third six-second exchange')
assert.ok(node.elapsed()<=20000)
assert.equal(node.run(3,1,0),0); assert.equal(node.attempts(),1,'Large first jitter leaves no full retry window')
assert.ok(node.elapsed()<=20000)
assert.equal(node.run(5,0,0),0); assert.equal(node.randoms(),3)
assert.deepEqual([node.jitter(0),node.jitter(1),node.jitter(2)],[100,200,300],'Fresh jitter on every attempt')
assert.equal(node.run(2,1,1),1); assert.equal(node.attempts(),2,'Retry budget survives millis wrap')
assert.equal(node.run(6,0,0),0); assert.equal(node.attempts(),3); assert.equal(node.receivers(),0)
assert.equal(node.run(7,0,0),0); assert.equal(node.attempts(),0)

// Exercise the actual Gateway packet-processing and cached reply functions.
const gatewayCpp = prelude + `
#define WIFI_HTTP_ENABLED 1
#define MAX_JSON_SIZE 256
#define MAX_PENDING_COMMANDS 1
struct FgFrameInfo {uint8_t slot;uint8_t generation[8];uint64_t sequence;};
struct FgGatewayDevice {bool valid;uint8_t generation[8];uint8_t key[32];uint64_t lastSequence;};
struct FgGatewayWatermark {uint8_t generation[8];uint64_t sequence;};
constexpr uint64_t FG_MAX_SEQUENCE=9007199254740991ULL;
FgGatewayDevice fgDevices[10]; bool fgRegistryReady=true, authValid=true;
unsigned long fgRegistrySyncedAt=0;int nvsWrites;
struct Command {bool used;String nodeId, generation, commandId, command;};
Command pendingCommands[1]; FgReplyCache fgReplyCaches[10];
uint8_t inputFrame[47]={};int readPosition,queueCalls,encryptCalls,replyWrites,sentReports,frameMismatch;
bool canQueue,canSend;uint8_t firstReply[255];size_t firstReplyLength;
struct Radio {
  int parsePacket() {readPosition=0;return 47;}
  bool available() {return readPosition<47;}
  int read() {return inputFrame[readPosition++];}
  int packetRssi() {return -40;} float packetSnr() {return 9;}
  void receive() {} void idle() {} void beginPacket() {}
  void write(const uint8_t* p,size_t n) {
    if(!replyWrites) {memcpy(firstReply,p,n);firstReplyLength=n;}
    else if(n!=firstReplyLength || memcmp(firstReply,p,n))frameMismatch++;
    replyWrites++;
  }
  bool endPacket() {return canSend;}
} LoRa;
struct Field {
  const char* key;
  template<typename T> void operator=(T) {}
  const char* operator|(const char*) {return equal(key,"id")?"NODE01":"s";}
};
template<int N> struct StaticJsonDocument {Field operator[](const char* key) {return {key};}
  bool overflowed() {return false;}};
template<int N> bool deserializeJson(StaticJsonDocument<N>&,String) {return false;}
template<int N> bool deserializeJson(StaticJsonDocument<N>&,uint8_t*,size_t) {return false;}
template<int N> void serializeJson(StaticJsonDocument<N>&,String& s) {s=String("command-json");}
String fgHex(const uint8_t*,size_t) {return "generation";}
String fgNodeId(uint8_t) {return "NODE01";}
String fgBase64(const uint8_t*,size_t) {return "encoded-frame";}
void lockPendingCommands() {} void unlockPendingCommands() {}
void lockFgDevices() {} void unlockFgDevices() {}
struct Preferences {
  bool begin(const char*,bool) {return true;}
  size_t putBytes(const char*,const void*,size_t n) {nvsWrites++;return n;}
  void end() {}
};
bool markPendingCommandSent(const String&,const String&) {sentReports++;return true;}
bool hasPendingCommandForNode(const String&,const String&) {return false;}
void clearAndRememberAcknowledgedCommand(const String&,const String&) {}
bool enqueuePacketForBackend(const String&) {queueCalls++;return canQueue;}
size_t fgEncryptBytes(const uint8_t* p,size_t n,const uint8_t*,const FgFrameInfo&,const char*,uint8_t* out) {
  encryptCalls++;memset(out,0,n+37);memcpy(out+21,p,n);return n+37;
}
${extract('radio_common/secure_frame.h','fgInspect')}
bool fgDecryptBytes(const uint8_t* p,size_t n,const uint8_t*,const char* direction,FgFrameInfo& info,uint8_t* plain,size_t& length) {
  if(!authValid || !fgInspect(p,n,direction,info))return false;
  length=n-37;memcpy(plain,p+21,length);return true; // GCM itself has separate independent fixtures.
}
${extract('gateway/secure_gateway.h','acceptFgUplink')}
${extract('gateway/gateway_commands.h','sendSecureReplyForNode')}
${extract('gateway/gateway_commands.h','resendCachedReply')}
${extract('gateway/packet_processing.h','handleIncomingLoRa')}
extern "C" void reset(int full,int failedTx) {
  fgReplyCaches[0]=FgReplyCache{};queueCalls=encryptCalls=replyWrites=sentReports=frameMismatch=0;
  canQueue=!full;canSend=!failedTx;nowMs=1;fgRegistryReady=authValid=true;fgRegistrySyncedAt=1;nvsWrites=0;
  fgDevices[0]=FgGatewayDevice{};fgDevices[0].valid=true;
  memcpy(inputFrame,"FGU1",4);inputFrame[4]=1;memset(inputFrame+5,0,16);inputFrame[20]=1;
  fgEncodeSensor(inputFrame+21,0,300,27.32f,70.29f,120);
  pendingCommands[0]={true,String("NODE01"),String("generation"),String("cmd_first"),String("gps_manual")};
}
extern "C" void incoming() {handleIncomingLoRa();nowMs+=7000;}
extern "C" void recover() {canQueue=canSend=true;pendingCommands[0].commandId=String("changed_after_first_reply");}
extern "C" int queues() {return queueCalls;}
extern "C" int encryptions() {return encryptCalls;}
extern "C" int replies() {return replyWrites;}
extern "C" int mismatch() {return frameMismatch;}
extern "C" int saves() {return nvsWrites;}
extern "C" void invalidate(int reason) {
  if(reason==1)fgDevices[0].valid=false;
  if(reason==2)fgRegistryReady=false;
  if(reason==3)fgDevices[0].generation[0]=1;
  if(reason==4)authValid=false;
  if(reason==5)nowMs=fgRegistrySyncedAt+30000;
  if(reason==6)inputFrame[46]^=1;
  if(reason==7)fgDevices[0].lastSequence=2;
}
`
const gateway=await compile('gateway',gatewayCpp)
for (const txFailed of [0,1]) {
  gateway.reset(0,txFailed);gateway.incoming();gateway.recover();gateway.incoming();gateway.incoming()
  assert.equal(gateway.queues(),1,'Duplicate never enters HTTP queue again')
  assert.equal(gateway.saves(),1,'Retry does not rewrite its sequence watermark')
  assert.equal(gateway.encryptions(),1,'One ciphertext only, including failed radio TX')
  assert.equal(gateway.replies(),3);assert.equal(gateway.mismatch(),0,'Same ACK bytes despite changed pending command')
}
gateway.reset(1,0);gateway.incoming()
assert.equal(gateway.replies(),0,'Queue-full request is not acknowledged')
gateway.recover();gateway.incoming();gateway.incoming()
assert.equal(gateway.queues(),2,'Identical request can retry after queue becomes available')
assert.equal(gateway.encryptions(),1);assert.equal(gateway.replies(),2)
for(const reason of [1,2,3,4,5,6]) {
  gateway.reset(0,0);gateway.incoming();gateway.invalidate(reason);gateway.incoming()
  assert.equal(gateway.queues(),1);assert.equal(gateway.replies(),1,
    'Cached retry still requires active registry, generation, authentication and exact bytes')
}
gateway.reset(0,0);gateway.incoming();gateway.invalidate(7);gateway.incoming()
assert.equal(gateway.queues(),1);assert.equal(gateway.replies(),2,
  'Cached ACK is still available after a command acknowledgement advanced the watermark')
console.log('FG1 C++ compact radio: codec, airtime, retry bytes, jitter, deadlines, rollover, queue-full recovery and cached ACK passed.')
