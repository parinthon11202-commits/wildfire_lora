from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


OUT = Path(__file__).resolve().parents[1] / "docs" / "figures" / "figure-3-7-sensor-node-transmission-v7.png"
W, H = 2000, 2700
BG = "white"
INK = "#111111"
MUTED = "#555555"
DECISION = "#f5f5f5"
PROCESS = "#ffffff"

REG = r"C:\Windows\Fonts\tahoma.ttf"
BOLD = r"C:\Windows\Fonts\tahomabd.ttf"
font = ImageFont.truetype(REG, 31)
font_small = ImageFont.truetype(REG, 25)
font_note = ImageFont.truetype(REG, 23)
font_bold = ImageFont.truetype(BOLD, 31)
font_caption = ImageFont.truetype(REG, 30)

img = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(img)


def centered_text(box, lines, fnt=font, fill=INK, spacing=8):
    x1, y1, x2, y2 = box
    if isinstance(lines, str):
        lines = lines.split("\n")
    heights = []
    widths = []
    for line in lines:
        bb = d.textbbox((0, 0), line, font=fnt)
        widths.append(bb[2] - bb[0])
        heights.append(bb[3] - bb[1])
    total_h = sum(heights) + spacing * (len(lines) - 1)
    y = y1 + (y2 - y1 - total_h) / 2
    for line, tw, th in zip(lines, widths, heights):
        d.text((x1 + (x2 - x1 - tw) / 2, y), line, font=fnt, fill=fill)
        y += th + spacing


def rect(cx, cy, w, h, text, fill=PROCESS, fnt=font, radius=0):
    box = (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)
    if radius:
        d.rounded_rectangle(box, radius=radius, fill=fill, outline=INK, width=3)
    else:
        d.rectangle(box, fill=fill, outline=INK, width=3)
    centered_text(box, text, fnt)
    return box


def diamond(cx, cy, w, h, text, fnt=font):
    pts = [(cx, cy - h / 2), (cx + w / 2, cy), (cx, cy + h / 2), (cx - w / 2, cy)]
    d.polygon(pts, fill=DECISION, outline=INK)
    d.line(pts + [pts[0]], fill=INK, width=3, joint="curve")
    centered_text((cx - w * .36, cy - h * .28, cx + w * .36, cy + h * .28), text, fnt)
    return pts


def circle(cx, cy, r, text, fnt=font_bold):
    box = (cx-r, cy-r, cx+r, cy+r)
    d.ellipse(box, fill=BG, outline=INK, width=3)
    centered_text(box, text, fnt)
    return box


def arrow(points, label=None, label_xy=None, fnt=font_small):
    d.line(points, fill=INK, width=4, joint="curve")
    (x1, y1), (x2, y2) = points[-2], points[-1]
    import math
    a = math.atan2(y2-y1, x2-x1)
    length, spread = 18, 0.52
    p1 = (x2-length*math.cos(a-spread), y2-length*math.sin(a-spread))
    p2 = (x2-length*math.cos(a+spread), y2-length*math.sin(a+spread))
    d.polygon([(x2, y2), p1, p2], fill=INK)
    if label and label_xy:
        d.text(label_xy, label, font=fnt, fill=INK)


CX = 800

# Entry and transmission/ACK loop
circle(CX, 75, 38, "A")
arrow([(CX, 113), (CX, 155)])
rect(CX, 220, 710, 130, ["สร้างแพ็กเก็ต JSON ข้อมูลวัด 1 ชุด", "พร้อมสถานะและเหตุผลการประเมิน"])
arrow([(CX, 285), (CX, 330)])
rect(CX, 380, 480, 100, "กำหนดจำนวนครั้งที่ส่ง = 1")
arrow([(CX, 430), (CX, 475)])
rect(CX, 550, 760, 150, ["สุ่มหน่วงเวลา 0–5 วินาทีและส่ง JSON ชุดเดิม", "หากส่งออกได้ เปิดรับ ACK/คำสั่งนาน 6 วินาที"])
arrow([(CX, 625), (CX, 690)])
diamond(CX, 785, 780, 190, ["ได้รับ ACK ที่ id, sid", "และ q ตรงกันหรือไม่?"])

# Retry branch to right
RX = 1580
arrow([(1190, 785), (1280, 785), (1280, 875), (RX, 875)], "ไม่ใช่", (1210, 735))
diamond(RX, 970, 650, 190, "ส่งครบ 3 ครั้ง\nแล้วหรือไม่?")
arrow([(RX, 1065), (RX, 1135)], "ยังไม่ครบ", (RX+22, 1080))
rect(RX, 1200, 470, 130, "เพิ่มจำนวนครั้งที่ส่ง")
arrow([(RX+235, 1200), (1900, 1200), (1900, 550), (1180, 550)], None)
arrow([(1255, 970), (1120, 970), (1120, 1180), (1195, 1180)], "ครบแล้ว\nไม่ได้รับ ACK", (1135, 985), fnt=font_note)

# Merge send result
arrow([(CX, 880), (CX, 940)], "ใช่", (CX+22, 890))
rect(CX, 990, 620, 100, "จบการส่งข้อมูลวัดชุดนี้")
arrow([(CX, 1040), (CX, 1120)])

# GPS service and energy management
rect(CX, 1180, 790, 120, ["ให้บริการ GPS และส่งรายงานพิกัดที่รออยู่", "เป็นแพ็กเก็ตแยกจากข้อมูลวัด"])
arrow([(CX, 1240), (CX, 1300)])
diamond(CX, 1380, 680, 160, "สถานะเป็น WARNING\nหรือไม่?")

# WARNING branch, left
arrow([(460, 1380), (230, 1380), (230, 1535)], "ใช่", (300, 1335))
rect(230, 1620, 400, 170, ["คงการทำงานไว้", "บริการ GPS และรอเวลาที่เหลือ", "ให้ครบคาบ 20 วินาที"], fnt=font_small)
arrow([(230, 1705), (230, 1770)])
circle(230, 1820, 48, "N")
d.text((65, 1885), "N = เริ่มรอบวัดถัดไป", font=font_note, fill=MUTED)

# Non-warning path
arrow([(CX, 1460), (CX, 1520)], "ไม่ใช่", (CX+22, 1475))
diamond(CX, 1610, 700, 180, ["GPS กำลังค้นพิกัด", "หรือมีรายงานรอส่งหรือไม่?"])

# GPS active branch to right
GX = 1570
arrow([(1150, 1610), (GX, 1610), (GX, 1710)], "ใช่", (1190, 1565))
rect(GX, 1795, 610, 170, ["ปิดไฟเซนเซอร์และบริการ GPS", "จนงานเสร็จหรือถึงรอบวัดถัดไป"])
arrow([(GX, 1880), (GX, 1940)])
diamond(GX, 2025, 570, 170, "ถึงเวลารอบวัด\nถัดไปแล้วหรือไม่?")
arrow([(1285, 2025), (1180, 2025), (1180, 2220), (1135, 2220)], "ไม่ใช่", (1190, 1980))
arrow([(1855, 2025), (1920, 2025), (1920, 2170)], "ใช่", (1850, 1980))
circle(1920, 2220, 48, "N")

# Deep sleep path
arrow([(CX, 1700), (CX, 2110)], "ไม่ใช่", (CX+22, 1730))
rect(CX, 2220, 670, 220, ["ปิดวิทยุและไฟเซนเซอร์", "เข้าสู่ Deep Sleep ตามเวลาที่เหลือ", "NORMAL 5 นาที • WATCH 2 นาที", "SENSOR_FAULT 5 นาที"], fnt=font_small)
arrow([(CX, 2330), (CX, 2380)])
rect(CX, 2440, 500, 120, ["ตื่นด้วยตัวจับเวลา", "และเริ่ม setup ใหม่"])
arrow([(CX, 2500), (CX, 2540)])
circle(CX, 2585, 42, "I")

# Notes/caption
d.text((90, 2645), "หมายเหตุ: I = เริ่มต้นระบบหลังตื่น; ACK ยืนยันว่า Gateway รับแพ็กเก็ตผ่าน LoRa เท่านั้น ไม่ได้ยืนยันการบันทึกบนเซิร์ฟเวอร์", font=font_note, fill=MUTED)

OUT.parent.mkdir(parents=True, exist_ok=True)
img.save(OUT, dpi=(220, 220))
print(OUT)
