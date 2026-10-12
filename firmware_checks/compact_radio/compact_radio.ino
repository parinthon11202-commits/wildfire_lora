// Optional self-check sketch: dummy keys only; no radio, sensors or NVS writes.
#include <Arduino.h>
#include <mbedtls/base64.h>
#include "../../radio_common/secure_frame.h"
#include "../../radio_common/radio_timing.h"
#include "../../radio_common/reply_cache.h"

void setup() {
  Serial.begin(115200);
  delay(1000);
  bool ok = true;
  uint8_t sensor[FG_SENSOR_BYTES];
  const uint8_t expectedPlain[] = {1, 0, 1, 0x2c, 0x0a, 0xac, 0x1b, 0x75, 0, 0x78};
  ok = fgEncodeSensor(sensor, 0, 300, 27.32f, 70.29f, 120) &&
    !memcmp(sensor, expectedPlain, sizeof(sensor));
  FgSensorValues value;
  ok = ok && fgDecodeSensor(sensor, sizeof(sensor), value) && value.temperature100 == 2732;
  ok = ok && fgEncodeSensor(sensor, 3, 300, -5.25f, NAN, -1) &&
    fgDecodeSensor(sensor, sizeof(sensor), value) && value.temperature100 == -525 &&
    value.humidity100 == FG_VALUE_MISSING && value.adc == FG_VALUE_MISSING;
  ok = ok && !fgEncodeSensor(sensor, 0, 300, NAN, 50, 120);

  const char *reference = "RkdVMQEBAgMEBQYHCAAAAAAAAAABXhJe7QkFmBLnBGD0nkP+SLduZG26W3lrwSE=";
  uint8_t expected[255]; size_t expectedLength = 0;
  ok = ok && mbedtls_base64_decode(expected, sizeof(expected), &expectedLength,
    (const unsigned char *)reference, strlen(reference)) == 0;
  uint8_t key[32] = {};
  FgFrameInfo info = {}; info.slot = 1; info.sequence = 1;
  for (int i = 0; i < 8; i++) info.generation[i] = i + 1;
  uint8_t frame[255];
  size_t length = fgEncryptBytes(expectedPlain, sizeof(expectedPlain), key, info, "FGU1", frame);
  ok = ok && length == 47 && expectedLength == length && !memcmp(frame, expected, length);
  uint8_t decoded[255]; size_t decodedLength = 0; FgFrameInfo result;
  ok = ok && fgDecryptBytes(frame, length, key, "FGU1", result, decoded, decodedLength) &&
    decodedLength == sizeof(expectedPlain) && !memcmp(decoded, expectedPlain, decodedLength);
  for (size_t index = 0; index < length; index++) {
    frame[index] ^= 1;
    if (fgDecryptBytes(frame, length, key, "FGU1", result, decoded, decodedLength)) ok = false;
    frame[index] ^= 1;
  }
  const uint8_t reply[] = {FG_REPLY_KIND, 1, 0};
  const size_t replyLength = fgEncryptBytes(reply, sizeof(reply), key, info, "FGD1", decoded);
  ok = ok && replyLength == 40;
  FgReplyCache cached;
  fgRememberRequest(cached, frame, length, 100);
  ok = ok && !cached.queued && fgCachedRequestMatches(cached, frame, length, 200);
  cached.queued = true; cached.replyLength = replyLength;
  memcpy(cached.reply, decoded, replyLength);
  frame[30] ^= 1;
  ok = ok && !fgCachedRequestMatches(cached, frame, length, 200);
  frame[30] ^= 1;
  ok = ok && !fgCachedRequestMatches(cached, frame, length, 60100);
  ok = ok && fgTimeOnAirMs(47, 10, 125000) == 576 &&
    fgTimeOnAirMs(40, 10, 125000, true) == 535;
  ok = ok && fgExchangeFits(12000, 20000, 1000, 576, 6000, 250) &&
    !fgExchangeFits(13000, 20000, 1000, 576, 6000, 250);
  // Real policy additionally reserves the largest command acknowledgement TX.
  ok = ok && !fgExchangeFits(12000, 20000, 0, 576, 6000,
    250 + fgTimeOnAirMs(255, 10, 125000));
  Serial.println(ok ? "FG_COMPACT_RADIO_PASS" : "FG_COMPACT_RADIO_FAIL");
}
void loop() { delay(1000); }
