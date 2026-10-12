#pragma once
#include <stdint.h>
#include <stddef.h>
#include <math.h>

// FG1 keeps its authenticated 21-byte header and 16-byte tag. These are plaintext
// payload layouts, not C++ structs on the wire (no padding or host endianness).
constexpr uint8_t FG_SENSOR_KIND = 1;
constexpr uint8_t FG_REPLY_KIND = 2;
constexpr size_t FG_SENSOR_BYTES = 10;
constexpr size_t FG_REPLY_BYTES = 3;
constexpr int16_t FG_TEMP_MISSING = INT16_MIN;
constexpr uint16_t FG_VALUE_MISSING = UINT16_MAX;

uint16_t fgReadU16(const uint8_t *bytes) {
  return ((uint16_t)bytes[0] << 8) | bytes[1];
}
void fgWriteU16(uint8_t *bytes, uint16_t value) {
  bytes[0] = value >> 8;
  bytes[1] = value & 255;
}

bool fgEncodeSensor(uint8_t *bytes, uint8_t state, uint16_t interval,
                    float temperature, float humidity, int adc) {
  if (state > 3 || interval == 0) return false;
  int16_t temperature100 = FG_TEMP_MISSING;
  uint16_t humidity100 = FG_VALUE_MISSING;
  if (isfinite(temperature) && temperature >= -327.67f && temperature <= 327.67f) {
    temperature100 = (int16_t)lroundf(temperature * 100.0f);
  }
  if (isfinite(humidity) && humidity >= 0.0f && humidity <= 655.34f) {
    humidity100 = (uint16_t)lroundf(humidity * 100.0f);
  }
  const uint16_t particle = adc >= 0 && adc <= 4095 ? (uint16_t)adc : FG_VALUE_MISSING;
  if (state != 3 && (temperature100 == FG_TEMP_MISSING || humidity100 == FG_VALUE_MISSING ||
                    particle == FG_VALUE_MISSING)) return false;
  bytes[0] = FG_SENSOR_KIND;
  bytes[1] = state;
  fgWriteU16(bytes + 2, interval);
  fgWriteU16(bytes + 4, (uint16_t)temperature100);
  fgWriteU16(bytes + 6, humidity100);
  fgWriteU16(bytes + 8, particle);
  return true;
}

struct FgSensorValues {
  uint8_t state;
  uint16_t interval;
  int16_t temperature100;
  uint16_t humidity100;
  uint16_t adc;
};
bool fgDecodeSensor(const uint8_t *bytes, size_t length, FgSensorValues &value) {
  if (length != FG_SENSOR_BYTES || bytes[0] != FG_SENSOR_KIND || bytes[1] > 3) return false;
  value.state = bytes[1];
  value.interval = fgReadU16(bytes + 2);
  // Arithmetic conversion is portable even for a compiler where uint16 -> int16
  // conversion outside the signed range is implementation-defined.
  const uint16_t temperature = fgReadU16(bytes + 4);
  value.temperature100 = temperature <= INT16_MAX ? (int16_t)temperature :
    (int16_t)((int32_t)temperature - 65536);
  value.humidity100 = fgReadU16(bytes + 6);
  value.adc = fgReadU16(bytes + 8);
  if (value.interval == 0 || (value.adc > 4095 && value.adc != FG_VALUE_MISSING)) return false;
  if (value.state != 3 && (value.temperature100 == FG_TEMP_MISSING ||
      value.humidity100 == FG_VALUE_MISSING || value.adc == FG_VALUE_MISSING ||
      value.temperature100 < -2000 || value.temperature100 > 8500 || value.humidity100 > 10000)) {
    return false;
  }
  return true;
}
