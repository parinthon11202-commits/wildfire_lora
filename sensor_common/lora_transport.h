#pragma once
#include "../radio_common/radio_timing.h"
#include "../radio_common/compact_packets.h"

/*
  การส่งข้อมูลผ่าน LoRa
  เริ่มวิทยุ สร้าง JSON ของข้อมูลเซนเซอร์ ส่งแพ็กเก็ต
  และเปิดช่วงรับ ACK หรือคำสั่ง GPS จาก Gateway หลังส่ง
*/

// initLoRa: ตั้ง SPI และวิทยุ LoRa แล้วคืน true ถ้าเริ่มได้; ค่าคลื่นต้องสอดคล้องกับ เกตเวย์ จึงสื่อสารกันได้
bool initLoRa() {
  lastLoRaInitAttemptMs = millis();
  SPI.begin(LORA_SCK, LORA_MISO, LORA_MOSI, LORA_SS);
  LoRa.setPins(LORA_SS, LORA_RST, LORA_DIO0);

  if (!LoRa.begin(LORA_FREQUENCY)) {
    loraReady = false;
    Serial.println("LoRa init FAILED");
    return false;
  }

  LoRa.setSpreadingFactor(LORA_SPREADING_FACTOR);
  LoRa.setSignalBandwidth(LORA_SIGNAL_BANDWIDTH);
  LoRa.setCodingRate4(LORA_CODING_RATE_DENOMINATOR);
  LoRa.setSyncWord(LORA_SYNC_WORD);
  LoRa.setTxPower(LORA_TX_POWER_DBM);
  LoRa.setPreambleLength(8);
  LoRa.disableCrc();
  Serial.println(
    String("LoRa init OK SF=") + LORA_SPREADING_FACTOR +
    " TX=" + LORA_TX_POWER_DBM + " dBm"
  );
  loraReady = true;
  return true;
}

// ensureLoRaReady: คืน true ถ้าวิทยุพร้อม มิฉะนั้นลองเริ่มใหม่เมื่อพ้นเวลารอ; ช่วยกู้การส่งหลัง เริ่มอุปกรณ์ ล้มเหลวโดยไม่ลองถี่ทุกครั้ง
bool ensureLoRaReady() {
  if (loraReady) return true;
  if (millis() - lastLoRaInitAttemptMs < LORA_INIT_RETRY_MS) return false;
  return initLoRa();
}

// buildJsonPacket: ประกอบค่าที่วัดและสถานะความเสี่ยงเป็น JSON ย่อสำหรับ LoRa
String buildJsonPacket(const SensorData &data, FireStatus status) {
  StaticJsonDocument<MAX_JSON_SIZE> doc;

  // โหนดส่งค่าที่วัดได้และสถานะความเสี่ยง
  doc["t"] = "s";
  doc["id"] = NODE_ID;
  doc["ri"] = plannedReportIntervalSeconds(status);
  doc["st"] = statusToString(status);
  doc["at"] = data.airTemp;
  doc["h"] = data.humidity;
  doc["adc"] = data.particleAdc;

  String payload;
  serializeJson(doc, payload);
  return payload;
}

// ประกาศล่วงหน้า (ยังไม่มีตัวฟังก์ชัน) เพื่อให้ฟังก์ชันส่งด้านล่างเรียกชื่อที่นิยามทีหลังได้
bool listenForGatewayCommand(bool waitForSensorAck);

uint32_t remainingRadioCycleMs() {
  if (!radioCycleBudgetMs) return UINT32_MAX;
  const uint32_t elapsed = millis() - radioCycleStartedMs;
  return elapsed >= radioCycleBudgetMs ? 0 : radioCycleBudgetMs - elapsed;
}

uint32_t radioExchangeCostMs(size_t frameLength, bool receiveReply) {
  const uint32_t txMs = fgTimeOnAirMs(frameLength, LORA_SPREADING_FACTOR, LORA_SIGNAL_BANDWIDTH);
  // A reply can carry a GPS command; reserve its largest possible cmd_ack TX as
  // well as the full six-second receive window, not just the normal ACK airtime.
  return txMs + RADIO_PROCESSING_GUARD_MS + (receiveReply ? COMMAND_RX_WINDOW_MS +
    fgTimeOnAirMs(255, LORA_SPREADING_FACTOR, LORA_SIGNAL_BANDWIDTH) : 0);
}

bool waitForRadioTurn(size_t frameLength, uint32_t maximumDelayMs, bool receiveReply = true) {
  const uint32_t cost = radioExchangeCostMs(frameLength, receiveReply);
  uint32_t remaining = remainingRadioCycleMs();
  if (remaining < cost) {
    if (!radioDeadlineLogged) {
      Serial.println("TX deferred: insufficient cycle time for a full exchange");
      radioDeadlineLogged = true;
    }
    return false;
  }
  const uint32_t maximum = min(maximumDelayMs, remaining - cost);
  const uint32_t delayMs = maximum ? random(0, maximum + 1) : 0;
  Serial.print("Random TX delay ms: ");
  Serial.println(delayMs);
  delay(delayMs);
  // Check again after scheduling delays; never cut an ACK window short to fit.
  return remainingRadioCycleMs() >= cost;
}

#if SECURE_LORA_ENABLED
bool sendCompactMeasurement(const SensorData &data, FireStatus status) {
  uint8_t payload[FG_SENSOR_BYTES];
  if (!fgEncodeSensor(payload, (uint8_t)status, plannedReportIntervalSeconds(status),
                      data.airTemp, data.humidity, data.particleAdc) || !ensureLoRaReady()) return false;
  uint8_t frame[FG_MAX_FRAME];
  size_t length = 0;
  for (unsigned attempt = 1; attempt <= SENSOR_TX_MAX_ATTEMPTS; attempt++) {
    if (!waitForRadioTurn(FG_HEADER + FG_SENSOR_BYTES + FG_TAG,
        attempt == 1 ? RANDOM_TX_DELAY_MAX_MS : RANDOM_RETRY_DELAY_MAX_MS)) break;
    // One reading -> one sequence/ciphertext. A retry MUST reuse these exact bytes.
    if (!length) length = prepareSecurePayload(payload, sizeof(payload), frame);
    if (!length) break;
    Serial.print("Sensor TX attempt: "); Serial.println(attempt);
    Serial.print("Radio frame bytes: "); Serial.println(length);
    const bool sent = transmitPreparedSecureFrame(frame, length);
    const bool acknowledged = sent && listenForGatewayCommand(true);
    Serial.print("Gateway ACK: "); Serial.println(acknowledged ? "YES" : "NO");
    if (acknowledged) return true;
    LoRa.sleep();
  }
  LoRa.sleep();
  return false;
}
#endif

// sendLoRaPacket: สุ่มเวลารอ ส่งหนึ่งครั้ง แล้วฟัง ACK/คำสั่ง GPS
bool sendLoRaPacket(const String &payload, bool useRandomDelay, bool requireGatewayAck = false) {
  if (!ensureLoRaReady()) {
    Serial.println("TX skipped: LoRa is not ready");
    return false;
  }

  const size_t wireLength = payload.length() +
#if SECURE_LORA_ENABLED
    FG_HEADER + FG_TAG;
#else
    0;
#endif
  if (!waitForRadioTurn(wireLength, useRandomDelay ? RANDOM_TX_DELAY_MAX_MS : 0)) return false;

#if SECURE_LORA_ENABLED
  bool ok = transmitSecurePayload(payload);
#else
  LoRa.idle();
  LoRa.beginPacket();
  LoRa.print(payload);
  bool ok = LoRa.endPacket();
#endif
  bool acknowledged = false;
  if (ok) acknowledged = listenForGatewayCommand(requireGatewayAck);
  else LoRa.sleep();

  Serial.print("TX bytes: ");
  Serial.println(payload.length());
  Serial.print("TX: ");
  Serial.println(payload);
  Serial.print("TX status: ");
  Serial.println(ok ? "OK" : "FAILED");
  if (requireGatewayAck) {
    Serial.print("Gateway ACK: ");
    Serial.println(acknowledged ? "YES" : "NO");
  }
  return ok && (!requireGatewayAck || acknowledged);
}
