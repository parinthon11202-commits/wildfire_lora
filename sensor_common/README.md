# โค้ดร่วมของ Sensor Node

โฟลเดอร์นี้ใช้ร่วมกันทั้ง managed FG1 (`provisioned_sensor`) และสเก็ตช์ legacy
managed FG1 รับ NODE_ID จาก config ที่ลงทะเบียนผ่าน USB; legacy กำหนดใน `config.h`
รายละเอียดแพ็กเก็ต 47 ไบต์, SF10 และการส่งซ้ำอยู่ใน [FG1 compact radio](../docs/FG1_COMPACT_RADIO.md)

## ลำดับอ่านสำหรับผู้เริ่มต้น

1. เปิด `provisioned_sensor/provisioned_sensor.ino` สำหรับระบบ FG1 ปัจจุบัน
2. ดู `config.h` ของโหนดนั้นเพื่อรู้ขาอุปกรณ์ เกณฑ์ และรอบเวลา
3. เริ่มอ่าน `setup()` และ `loop()` ที่ท้ายไฟล์ `.ino`
4. เปิด `node_app.h` เพื่อดู `setupNode()` และ `runOneMeasurementCycle()`
5. ตามไปยังไฟล์ที่ตรงกับงานที่ต้องการศึกษา

## หน้าที่ของแต่ละไฟล์

- `node_state.h` — รูปแบบข้อมูลและตัวแปรที่ใช้ร่วมกัน
- `sensor_config.h` — ขาอุปกรณ์ เกณฑ์ และรอบเวลาที่ใช้ร่วมกัน
- `node_helpers.h` — ฟังก์ชันช่วยทั่วไปและข้อความ Serial
- `sensor_reading.h` — อ่าน SHT31 และอ่าน Sharp GP2Y1014AU0F สามครั้งเพื่อใช้ค่ากลาง
- `risk_rules.h` — ตรวจ SENSOR_FAULT แล้วเทียบค่ากับเกณฑ์ NORMAL, WATCH หรือ WARNING
- `lora_transport.h` — ส่ง compact FG1, สุ่มเวลา/ลองซ้ำ และตรวจเวลาเหลือในรอบ; JSON สำหรับ GPS/legacy
- `gps_service.h` — ค้นหา บันทึก และรายงานพิกัด
- `gateway_commands.h` — รับคำสั่ง GPS จาก Gateway และตอบรับคำสั่ง
- `power_management.h` — ควบคุมรอบเวลาและ deep sleep
- `node_app.h` — ขั้นตอนเตรียมโหนดและลำดับรอบวัดที่ `.ino` เรียกใช้

ทุกฟังก์ชันมีคำอธิบายอยู่เหนือฟังก์ชันนั้นโดยตรง
