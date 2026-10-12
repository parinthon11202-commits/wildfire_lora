#pragma once
#include <stdint.h>
#include <stddef.h>

// Semtech time-on-air formula: explicit header, preamble 8, coding rate 4/5.
// Returns a ceiling in milliseconds, including low-data-rate optimization.
uint32_t fgTimeOnAirMs(size_t bytes, uint8_t sf, uint32_t bandwidth, bool crc = false) {
  const uint32_t symbols = 1UL << sf;
  const int de = (uint64_t)symbols * 1000 > (uint64_t)bandwidth * 16 ? 1 : 0;
  const int numerator = 8 * (int)bytes - 4 * sf + 28 + (crc ? 16 : 0);
  const int denominator = 4 * (sf - 2 * de);
  const int groups = numerator > 0 ? (numerator + denominator - 1) / denominator : 0;
  const uint32_t payloadSymbols = 8 + groups * 5;
  // Four times symbol count represents the 4.25-symbol fixed preamble overhead.
  const uint64_t numeratorMs = (uint64_t)(4 * (8 + payloadSymbols) + 17) * symbols * 1000;
  const uint64_t denominatorMs = (uint64_t)4 * bandwidth;
  return (uint32_t)((numeratorMs + denominatorMs - 1) / denominatorMs);
}

bool fgExchangeFits(uint32_t elapsed, uint32_t budget, uint32_t delayMs,
                    uint32_t txMs, uint32_t rxMs, uint32_t reserveMs) {
  return elapsed < budget &&
    (uint64_t)delayMs + txMs + rxMs + reserveMs <= budget - elapsed;
}
