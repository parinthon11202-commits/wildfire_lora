# Wildfire LoRa — SHT31 + Sharp GP2Y1014AU0F

> FG1 node registration: ใช้บอร์ดเดิม เพิ่ม USB provisioning,
> NODE01–NODE10, soft deletion และ authenticated/encrypted LoRa ไม่ใช่ LoRaWAN
> Backend compact และเว็บพร้อมเฟิร์มแวร์โหนด 1.2.1 deploy VM แล้ววันที่ 12 ตุลาคม 2569
> ตรวจ API / ไฟล์เฟิร์มแวร์ผ่านโดเมนจริงแล้ว; ยังไม่ได้ flash โหนดหรือ Gateway ในรอบนี้
> ปุ่มเพิ่ม/ติดตั้งโหนดใช้ไฟล์ใหม่ผ่าน USB; Gateway และโหนดต้องใช้ SF10 ตรงกัน
> ดู [คู่มือ FG1](docs/FG1_ONBOARDING.md) สำหรับขั้นตอนที่เหลือและข้อจำกัด
> รูปแบบแพ็กเก็ตและนโยบายลองซ้ำ: [FG1 compact radio](docs/FG1_COMPACT_RADIO.md)
> โหนด legacy ด้านล่างใช้กับ Gateway/Backend FG1 ไม่ได้ ต้องวางแผน migration ก่อน

ระบบต้นแบบตรวจสัญญาณบ่งชี้ไฟป่าจากอุณหภูมิอากาศ ความชื้นสัมพัทธ์ และอนุภาคในอากาศ
โดย Sensor Node ตัดสินสถานะแล้วส่งผ่าน LoRa ไป Gateway, Backend และ Dashboard

ระบบใช้สถานะ `NORMAL`, `WATCH`, `WARNING` และ `SENSOR_FAULT` ตามเกณฑ์ที่กำหนดไว้ในโค้ด

## เกณฑ์สถานะ

โหนดตรวจเซนเซอร์ก่อน ถ้าอ่านผิดปกติจะเป็น `SENSOR_FAULT` มิฉะนั้นจึงตรวจ `WARNING`, `WATCH` และ `NORMAL`

| สถานะ | เงื่อนไข |
|---|---|
| `SENSOR_FAULT` | อุณหภูมิ/ความชื้นอ่านไม่ได้หรือหลุดช่วงเซนเซอร์ หรือ ADC หลุดช่วง 0–4095 |
| `WARNING` | อุณหภูมิ `> 45°C` **หรือ** ค่าควัน `ADC > 1100` **หรือ** อุณหภูมิ `>= 30°C` พร้อมความชื้น `<= 30%RH` |
| `WATCH` | ยังไม่เป็น `WARNING` และอุณหภูมิ `> 35°C` **หรือ** ค่าควัน `ADC > 300` **หรือ** ความชื้น `< 50%RH` |
| `NORMAL` | อุณหภูมิ `<= 35°C` และค่าควัน `ADC <= 300` และความชื้น `>= 50%RH` |

เงื่อนไขอุณหภูมิ `>= 30°C` ร่วมกับความชื้น `<= 30%RH` คือการใช้สองปัจจัยที่โครงการวัดได้
จากแนวคิด 30-30-30 โดยระบบไม่มีเซนเซอร์ความเร็วลม จึงไม่กล่าวอ้างว่าใช้กฎครบสามปัจจัย

รายละเอียดขอบเขตและตัวอย่างอยู่ใน
[`docs/node-risk-rules.md`](docs/node-risk-rules.md)

## รอบวัดและส่งข้อมูลภาคสนาม

| สถานะ | รอบวัดและส่ง | การทำงาน |
|---|---:|---|
| `NORMAL` | 1 นาที | Deep sleep ระหว่างรอบ |
| `WATCH` | 40 วินาที | Deep sleep ระหว่างรอบ |
| `WARNING` | 20 วินาที | ทำงานต่อเนื่องโดยไม่ Deep sleep |
| `SENSOR_FAULT` | 1 นาที | Deep sleep ระหว่างรอบ |

คาบเป็นแบบเริ่มรอบถึงเริ่มรอบ โค้ดจึงหักเวลาอ่านเซนเซอร์ ส่ง LoRa และฟังคำสั่ง GPS ออกจากเวลาที่เหลือ
ถ้ารอบส่งใช้เวลานานกว่า 20 วินาที รอบถัดไปจะเริ่มทันทีเมื่อรอบเดิมจบ

managed node ใช้แพ็กเก็ตเซนเซอร์ 47 ไบต์ และ SF10/BW125 kHz เหมือน Gateway
หน่วงครั้งแรกสุ่ม 0–10 วินาที และลองซ้ำสุ่มใหม่ 0–3 วินาที รวมไม่เกิน 3 ครั้งต่อค่าที่วัดหนึ่งชุด
ได้ ACK ที่ถูกต้องจบรอทันที; ไม่ได้ ACK รอสูงสุด 6 วินาทีหลังส่งแต่ละครั้ง
ถ้าเวลาในรอบไม่พอสำหรับการส่ง/รอ ACK/ตอบคำสั่งเต็มชุดจะไม่เริ่มครั้งนั้น
รอบ WARNING จึงอาจส่งเพียง 1–2 ครั้ง ไม่รับประกันครบ 3 ครั้ง หรือส่งครบสิบโหนดทุก 20 วินาที
ต้องทดสอบหลายโหนดเปิดพร้อมกันและระยะส่งจริงก่อนสรุปความน่าเชื่อถือ

## การวัดควันด้วย Sharp

Sharp GP2Y1014AU0F อ่าน ADC ดิบ 3 ครั้งตามจังหวะใน datasheet แล้วใช้ค่ากลาง โดยไม่แปลงเป็น µg/m³

ค่า ADC เป็นค่าดิบของบอร์ดในช่วง 0–4095 ไม่ใช่ PM2.5 หรือความเข้มข้นที่สอบเทียบแล้ว
เกณฑ์ `300/1100` จึงเป็นเกณฑ์ทดลองของต้นแบบที่ต้องทดสอบกับฮาร์ดแวร์จริง

## แพ็กเก็ต Sensor

ตัวอย่างข้อมูลหลังถอดรหัส (ไม่ใช่ข้อความที่ส่งบนคลื่นสำหรับ managed node):

```json
{"t":"s","id":"NODE01","ri":20,"st":"WARNING","at":30,"h":30,"adc":1200}
```

- `st`: สถานะที่เฟิร์มแวร์ตัดสิน
- `ri`: รอบรายงานที่โหนดกำหนด หน่วยวินาที
- `at`, `h`, `adc`: อุณหภูมิ ความชื้น และค่าควัน ADC ดิบ
บนคลื่น FG1 เข้ารหัส payload ไบนารี 10 ไบต์ พร้อม header 21 และ tag 16 รวม 47 ไบต์
Backend ตรวจตัวตน รูปแบบและค่าที่รับ แต่ไม่คำนวณเกณฑ์ความเสี่ยงแทนโหนด

## โครงสร้างสำคัญ

```text
sensor_node/          เฟิร์มแวร์ NODE01
sensor_node_2/        เฟิร์มแวร์ NODE02
sensor_common/        ฟังก์ชันร่วมของทั้งสองโหนด แยกตามหน้าที่เป็นไฟล์ .h
provisioned_sensor/   เฟิร์มแวร์ FG1 กลาง ลงทะเบียน NODE01–NODE10 ผ่าน USB
radio_common/         รูปแบบ FG1, compact payload, airtime และ cached reply
gateway/              เฟิร์มแวร์ Gateway แยกไฟล์รับ LoRa, HTTP และคำสั่งตามหน้าที่
wildfire-backend/     API, MongoDB, Alert และ Telegram
wildfire-dashboard/   หน้าเว็บสถานะ แผนที่ และกราฟ
tools/test_node_risk.mjs  ทดสอบฟังก์ชัน C++ จริงของทั้งสองโหนด
```

## ไลบรารี Arduino

- LoRa by Sandeep Mistry
- ArduinoJson
- WiFiManager 2.0.17 (ใช้เฉพาะ Gateway)
- Adafruit SHT31 Library
- Adafruit BusIO
- TinyGPSPlus

บอร์ดที่ใช้คอมไพล์คือ `esp32:esp32:ttgo-lora32` การตั้งขา SHT31, Sharp, GPS และ LoRa
อยู่ใน `config.h` ของแต่ละสเก็ตช์ ทั้ง Gateway และ Sensor Node ต้องใช้ความถี่, spreading factor,
bandwidth, coding rate และ sync word ตรงกัน

## วิธีอัปโหลด

1. อัปโหลด `sensor_node/sensor_node.ino` เป็น `NODE01`
2. อัปโหลด `sensor_node_2/sensor_node_2.ino` เป็น `NODE02`
3. คัดลอก `gateway/secrets.example.h` เป็น `gateway/secrets.h` แล้วใส่ API key และใบรับรอง
4. อัปโหลด `gateway/gateway.ino` และตั้ง Wi-Fi ผ่านหน้า `Wildfire-Gateway-*`

อย่าถือผลการทดสอบซอฟต์แวร์แทนการสอบเทียบเซนเซอร์ การทดสอบระยะ LoRa และการทดสอบไฟเลี้ยงจริง

## คำสั่งตรวจโครงการ

```powershell
node tools/test_node_risk.mjs
node tools/test_node_ack.mjs
node tools/test_compact_radio.mjs
cd wildfire-backend
npm test
cd ..\wildfire-dashboard
npm test
npm run lint
npm run build
```

สำหรับ Arduino CLI ให้เพิ่มคลังที่ติดตั้งไว้และคอมไพล์ทั้งสามสเก็ตช์ด้วย FQBN เดียวกัน

## Domain deployment

ระบบโดเมนใช้ Backend ตัวเดียวเผยแพร่สอง hostname ผ่าน Cloudflare Tunnel:

- `https://wildfire.nattaphat.me` เป็น Dashboard อ่านอย่างเดียว
- `https://admin.nattaphat.me` ป้องกันด้วย Cloudflare Access สำหรับ GPS, ตำแหน่ง manual และจัดการ Alert

เริ่มระบบเวอร์ชันโดเมนด้วย:

```powershell
cd C:\wildfire_lora
.\start-domain.ps1
```

รายละเอียด Gateway และการตั้ง Wi-Fi อยู่ใน [`gateway/README.md`](gateway/README.md)

คำอธิบายโฟลเดอร์ ไฟล์ และฟังก์ชันสำคัญอยู่ใน [`docs/code-structure.md`](docs/code-structure.md)

โครงสร้าง Collection, field และ index ของ MongoDB อยู่ใน [`docs/database-schema.md`](docs/database-schema.md)
