# FG1 compact radio / retry policy

Backend/เว็บพร้อมเฟิร์มแวร์โหนด 1.2.1 deploy VM แล้ววันที่ 12 ตุลาคม 2569; ยังไม่ได้ flash บอร์ด
ไม่เปลี่ยน key/generation, การลงทะเบียน, Node document หรือประวัติย้อนหลัง
ยังใช้ AES-256-GCM และ Gateway เดิมหนึ่งตัว ไม่ใช่ LoRaWAN

## Sensor: 47 ไบต์

header 21 + encrypted sensor payload 10 + authentication tag 16
header เดิม: `FGU1` 4, slot 1, generation 8, sequence 8 (big-endian)
header ทั้งหมดเป็น AAD; nonce = direction 4 + sequence 8

| Offset ใน plaintext | จำนวนไบต์ | ค่า |
|---|---:|---|
| 0 | 1 | ชนิด sensor = 1 |
| 1 | 1 | NORMAL=0, WATCH=1, WARNING=2, SENSOR_FAULT=3 |
| 2 | 2 | ช่วงรายงานวินาที uint16 |
| 4 | 2 | อุณหภูมิ int16 ×100 |
| 6 | 2 | ความชื้น uint16 ×100 |
| 8 | 2 | ADC uint16 |

จำนวนเต็มทุกช่องเป็น big-endian; ไม่ส่ง C++ struct/padding บนคลื่น
ตัวอย่าง 27.32°C, 70.29%RH, ADC 120, NORMAL, 60 วินาที:
`01 00 00 3C 0A AC 1B 75 00 78` (ก่อนเข้ารหัส ไม่ใช่ ciphertext)
Backend ถอดกลับเป็น `{t:'s', id:'NODE01', ri:60, st:'NORMAL', at:27.32, h:70.29, adc:120}`
รูปแบบข้อมูลที่เว็บ/MongoDB/Telegram ใช้จึงไม่เปลี่ยน

โหนดตัดสินความเสี่ยงจากค่าที่อ่านก่อนปัดสองตำแหน่ง ไม่ใช้ค่าปัดแทนเกณฑ์เดิม
อ่านไม่ได้/เกินขอบเขตที่เก็บได้: temperature=-32768, humidity/ADC=65535
รับ sentinel เฉพาะ SENSOR_FAULT และถอดเป็น null ไม่แปลงเป็นศูนย์

## Reply: ปกติ 40 ไบต์

header เดิมแต่ direction=`FGD1`, slot/generation/sequence ตรงกับ uplink
plaintext `02 01 00`: reply=2, sensor ACK=1, ไม่มีคำสั่ง=0
GPS reply ใช้ ACK=0; flag=1 เมื่อมี JSON `{cmd,cid}` แนบท้าย 3 ไบต์
ดังนั้น ACK ที่มีคำสั่งยาวกว่า 40 ไบต์ GPS และ cmd_ack ยังใช้ authenticated JSON
โหนดตรวจ AES-GCM, slot, generation, sequence และรูปแบบ reply ก่อนยอมรับ ACK

## การส่งและลองซ้ำ

1. อ่านเซนเซอร์/ตัดสินสถานะ หนึ่งชุดต่อรอบ
2. หน่วงสุ่มครั้งแรก 0–10,000 ms; ลดเพดานอีกหากเวลาเหลือไม่พอ
3. จัด sequence/เข้ารหัสครั้งเดียวแล้วส่ง; รอ ACK สูงสุด 6,000 ms หลังส่งเสร็จ
4. ได้ ACK ถูกต้อง → จัดการคำสั่งที่แนบก่อน แล้วจบรอ/หยุดส่งซ้ำ
5. ไม่ได้ ACK → สุ่มใหม่ 0–3,000 ms แล้วส่ง **เฟรมเดิมทุกไบต์** หากยังเหลือเวลาพอ
6. รวมไม่เกิน 3 ครั้ง (ครั้งแรก + ลองซ้ำ 2) ถ้าไม่พอเวลาให้หยุด ไม่ตัด RX ให้สั้นลง

NORMAL/WATCH/SENSOR_FAULT เข้าสู่เส้นทางหลับเดิมถ้าไม่มีงาน GPS ค้าง
WARNING ไม่ deep sleep และรอรอบวัดถัดไป 20 วินาทีตามเดิม
ได้ ACK ไม่ได้หมายความว่าจะปิด ESP32 ทันทีหากสถานะ/งาน GPS ต้องให้เครื่องตื่น

เวลานับจากเริ่มรอบก่อนอ่านเซนเซอร์; งบ NORMAL=60s, WATCH=40s, WARNING=20s, FAULT=60s
ก่อนเริ่มทุก exchange กันเวลา TX + RX 6s + cmd_ack ใหญ่สุด 255 ไบต์ + guard 250ms
ที่ SF10 sensor ต้องเหลืออย่างน้อย `576 + 6000 + 2255 + 250 = 9081 ms` ก่อนรวม backoff
ตัวอย่าง WARNING: ผ่านไป 12,000 ms เหลือ 8,000 ms จึง **ไม่เริ่ม** ส่งครั้งใหม่
ใช้ reserve เผื่อมีคำสั่ง GPS ใน ACK แม้ส่วนใหญ่ไม่มีคำสั่ง จึงอาจลองได้เพียง 1–2 ครั้ง
guard ไม่ใช่การรับประกันเวลาหากฮาร์ดแวร์/driver ค้าง ต้องตรวจจริง

## Gateway ไม่สร้างข้อมูลซ้ำจาก radio retry

ตรวจ registry ที่ยังไม่หมดอายุ, generation และ GCM ก่อนเสมอ
request ใหม่บันทึก watermark ใน NVS ตามเดิม เก็บ request ล่าสุดต่อ slot ใน RAM
เข้าคิว Backend สำเร็จจึงสร้าง ACK และเก็บ ciphertext **ก่อน** ส่งทาง LoRa
request เดิมตรงทุกไบต์ภายใน 60s → ส่ง ciphertext ACK เดิม ไม่เข้าคิว HTTP ซ้ำ
ห้ามเปลี่ยนคำสั่งแล้วเข้ารหัส reply ใหม่ด้วย sequence เดิม เพราะจะใช้ GCM nonce ซ้ำ
คิวเต็ม → ไม่ ACK; request เดิมลองเข้าคิวได้อีกเมื่อโหนดลองซ้ำและคิวว่าง
cache RAM ใช้ประมาณ 5.2 KB สำหรับสิบ slot, หายเมื่อ reset; watermark NVS ไม่หาย
reset ระหว่างรอ ACK อาจทำให้ retry ถูกทิ้ง แล้วรอค่ารอบใหม่ ไม่รับประกันข้อมูลทุกชุดส่งถึง
Backend ตรวจ GCM อีกครั้งและใช้ atomic sequence CAS ปฏิเสธข้อมูลซ้ำ
ACK หมายถึงตรวจผ่านและเข้าคิว Gateway ไม่ได้ยืนยัน MongoDB commit
ความล้มเหลวของ HTTP upload ยังไม่เพิ่ม retry ในการแก้ radio ครั้งนี้

## วิทยุและเวลาบนคลื่น

ทั้งสองฝั่ง SF10, BW125 kHz, CR4/5, preamble 8, explicit header, sync word 0x34
คง CRC ตามทิศทางเดิม: uplink ไม่มี PHY CRC, downlink มี PHY CRC; GCM tag ยังตรวจข้อมูลครบ
สูตร airtime: sensor 47 ไบต์ ≈0.575488s, ACK 40 ไบต์ ≈0.534528s รวม≈1.110016s
ตัวเลขมาจากสูตร ไม่ใช่ค่าที่จับเวลาจากบอร์ด ไม่รวม backoff/อ่านเซนเซอร์/ประมวลผล/GPS
SF10 ลดเวลาครองคลื่น แต่ระยะ/ความทนสัญญาณอาจลดเมื่อเทียบ SF12 ต้องทดสอบพื้นที่เดิม
การสุ่มลดโอกาสชน ไม่รับประกันสิบโหนดส่ง WARNING ทุก20sพร้อมกันสำเร็จทุกครั้ง

## ตรวจและเปลี่ยนรุ่น

รัน backend tests, `tools/test_node_risk.mjs`, `tools/test_node_ack.mjs`, `tools/test_compact_radio.mjs`
C++ host tests mock วิทยุ/เวลา/crypto แต่ใช้ retry, codec, queue และ cache path จริง
`firmware_checks/compact_radio` ใช้ dummy key ตรวจ mbedTLS เทียบ fixture; ต้อง run บนบอร์ดจึงยืนยันผลได้
คอมไพล์ทั้ง provisioned_sensor และ Gateway ด้วย profile ESP32 เดิม
Gateway build ที่ใช้ dummy secrets เป็น compile check เท่านั้น **ห้ามนำไป flash ใช้งานจริง**
เผยแพร่ node firmware รุ่น1.2.1ผ่าน publisher ซึ่งสำรอง binary เก่าใน .codex-build/firmware-releases
ต้อง deploy Backend ที่รู้จัก compact ก่อน แล้วอัป Gateway และโหนดให้ใช้ SF10 ตรงกัน
ถ้า flash รักษา partition/NVS ตาม installer เดิม ไม่ต้องลบประวัติหรือลงทะเบียนใหม่เพื่อเปลี่ยน SF
การกดเพิ่ม/ติดตั้งใหม่ใช้ key/generation ที่เตรียมไว้ในไฟล์ Backend; หากคู่เดิมเคยเปิดใช้งานแล้วต้องเตรียมคู่ใหม่ก่อน

ผลตรวจ local วันที่ 12 ตุลาคม 2569: Backend 28/28, Dashboard 16/16, C++ risk/ACK/compact retry tests ผ่าน
TypeScript และ production build ผ่าน; manifest 1.2.0/ทุก checksum/USB markers ตรวจผ่าน
คอมไพล์โหนดผ่าน (flash 74%, static RAM 15%), Gateway dummy ผ่าน (flash 90%, static RAM 18%)
และ compact_radio self-check คอมไพล์ผ่าน แต่ยังไม่ได้รันบนบอร์ด
Gateway binary ใน .codex-build/compact-gateway ใช้ dummy key/CA ไม่ใช่ไฟล์สำหรับใช้งานจริง
ใช้ sandbox สำหรับ Backend/C++ tests; compiler ESP32 และ Dashboard tests ใช้นอก sandbox ตามที่ผู้ใช้อนุญาต
ไม่มีการ flash, deploy หรือ push GitHub ในรอบนี้

รุ่น 1.2.1 เปลี่ยนเฉพาะรอบวัด/ส่ง: NORMAL 60s, WATCH 40s, WARNING 20s, SENSOR_FAULT 60s
คงเกณฑ์ตัดสินสถานะ, ช่วงสุ่มส่ง, ACK 6s, การลองซ้ำ และการลงทะเบียนเดิม
ทดสอบฟังก์ชัน C++ จริงครบสี่ช่วงเวลา รวมการหักเวลางานและ clock rollover ผ่าน
ชุดทดสอบ compact/retry/ACK และ Backend 28/28 ผ่าน; โหนดคอมไพล์ผ่านและเตรียมไฟล์เว็บในเครื่อง
ค่า ri ใหม่จะทำให้ Backend ปรับ offline timeout ตามสองรอบโดยอัตโนมัติ ไม่ต้องเปลี่ยน Gateway ในการแก้รอบเวลาเพียงอย่างเดียว
ยังไม่ได้ flash/deploy หรือจับเวลารอบจริงหลังตื่นบนบอร์ด; การเริ่มบอร์ด/เซนเซอร์อาจเพิ่มเวลาจากคาบเป้าหมาย

## ผล deploy VM วันที่ 12 ตุลาคม 2569

image `forestguard-backend:fg1-1.2.1-20261012-110703` เปิดใช้งานแล้ว
ทดสอบ Backend 28/28 ใน container แยกไม่มี network ก่อนเปลี่ยนจริง และตรวจ firmware checksum ผ่าน
สลับเฉพาะ Backend/Cloudflare Tunnel; MongoDB container เดิมไม่ถูกหยุดและไม่ได้แก้ไฟล์ค่าลับ
ตรวจผ่าน `wildfire.nattaphat.me`: health HTTP 200, manifest 1.2.1 และ SHA-256 ทั้งสี่ไฟล์ตรงกับ build ในเครื่อง
`admin.nattaphat.me` ยัง redirect ไป Cloudflare Access สำหรับผู้ที่ไม่ได้ login
backup image และโค้ดเดิมอยู่ใน `/home/azureuser/forestguard-releases/fg1-release-1.2.1-20261012-110703/backup`
ใช้ปุ่มในหน้า Admin ติดตั้งโหนดผ่าน USB; Gateway ต้องเป็นรุ่น SF10 เช่นเดียวกับโหนดใหม่
การ deploy VM ไม่เปลี่ยนโปรแกรมที่อยู่ในบอร์ด จึงยังไม่ยืนยันคาบวัด/LoRa จากฮาร์ดแวร์จริง
