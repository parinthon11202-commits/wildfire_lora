from pathlib import Path
from math import atan2, cos, sin, pi

from PIL import Image, ImageDraw, ImageFont


WIDTH, HEIGHT, SCALE = 1800, 3700, 2
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "sensor-node-flowchart-thesis-v2.png"
PAGE_OUT = ROOT / "sensor-node-flowchart-page41-v2.png"
FONT_PATH = Path(r"C:\Windows\Fonts\tahoma.ttf")


def s(v):
    return int(round(v * SCALE))


img = Image.new("RGB", (s(WIDTH), s(HEIGHT)), "white")
d = ImageDraw.Draw(img)
font = ImageFont.truetype(str(FONT_PATH), s(34))
font_small = ImageFont.truetype(str(FONT_PATH), s(28))
font_tiny = ImageFont.truetype(str(FONT_PATH), s(22))
font_branch = ImageFont.truetype(str(FONT_PATH), s(28))
font_connector = ImageFont.truetype(str(FONT_PATH), s(27))

STROKE = "#202124"
DECISION_FILL = "#f4f5f6"
STATUS_FILL = "#f8f8f8"


def rect(x, y, w, h, fill="white"):
    d.rectangle((s(x), s(y), s(x + w), s(y + h)), fill=fill, outline=STROKE, width=s(3))


def ellipse(x, y, w, h, fill="white"):
    d.ellipse((s(x), s(y), s(x + w), s(y + h)), fill=fill, outline=STROKE, width=s(3))


def diamond(cx, cy, hw, hh):
    pts = [(s(cx), s(cy - hh)), (s(cx + hw), s(cy)), (s(cx), s(cy + hh)), (s(cx - hw), s(cy))]
    d.polygon(pts, fill=DECISION_FILL)
    d.line(pts + [pts[0]], fill=STROKE, width=s(3), joint="curve")


def connector(cx, cy, label):
    r = 28
    d.ellipse((s(cx - r), s(cy - r), s(cx + r), s(cy + r)), fill="white", outline=STROKE, width=s(3))
    bbox = d.textbbox((0, 0), label, font=font_connector)
    d.text((s(cx) - (bbox[2] - bbox[0]) / 2, s(cy) - (bbox[3] - bbox[1]) / 2 - bbox[1]), label, fill=STROKE, font=font_connector)


def centered(cx, cy, lines, fonts=None, gaps=None):
    if isinstance(lines, str):
        lines = [lines]
    if fonts is None:
        fonts = [font] * len(lines)
    if gaps is None:
        gaps = [6] * max(0, len(lines) - 1)
    metrics = []
    for text, fnt in zip(lines, fonts):
        bb = d.textbbox((0, 0), text, font=fnt)
        metrics.append((bb, bb[3] - bb[1]))
    total = sum(h for _, h in metrics) + sum(s(g) for g in gaps)
    yy = s(cy) - total / 2
    for i, (text, fnt) in enumerate(zip(lines, fonts)):
        bb, height = metrics[i]
        width = bb[2] - bb[0]
        d.text((s(cx) - width / 2, yy - bb[1]), text, fill=STROKE, font=fnt)
        yy += height
        if i < len(gaps):
            yy += s(gaps[i])


def arrow(points, head=True):
    pts = [(s(x), s(y)) for x, y in points]
    d.line(pts, fill=STROKE, width=s(3), joint="curve")
    if not head:
        return
    (x1, y1), (x2, y2) = points[-2], points[-1]
    angle = atan2(y2 - y1, x2 - x1)
    length, spread = 16, pi / 7
    p1 = (x2 - length * cos(angle - spread), y2 - length * sin(angle - spread))
    p2 = (x2 - length * cos(angle + spread), y2 - length * sin(angle + spread))
    d.polygon([(s(x2), s(y2)), (s(p1[0]), s(p1[1])), (s(p2[0]), s(p2[1]))], fill=STROKE)


def branch_label(x, y, text):
    d.text((s(x), s(y)), text, fill=STROKE, font=font_branch)


# Top-level initialization
ellipse(770, 25, 260, 85)
centered(900, 67, "เริ่มต้น")
arrow([(900, 110), (900, 150)])

rect(560, 155, 680, 120)
centered(900, 215, ["โหลด Baseline และข้อมูลจาก NVS", "เริ่มต้นบอร์ด เซนเซอร์ LoRa และ GPS"])

# Connector I returns here after timer wake.
connector(1325, 215, "I")
arrow([(1297, 215), (1245, 215)])

arrow([(900, 275), (900, 320)])
rect(560, 325, 680, 100)
centered(900, 375, ["อ่านค่า SHT31 และ Sharp GP2Y1014AU0F"])

# Connector N starts a new awake measurement cycle without reinitializing hardware.
connector(485, 375, "N")
arrow([(513, 375), (555, 375)])

arrow([(900, 425), (900, 475)])
diamond(900, 560, 285, 85)
centered(900, 560, ["ข้อมูลเซนเซอร์", "ถูกต้องหรือไม่?"])

# Invalid sensor branch
branch_label(590, 510, "ไม่")
arrow([(615, 560), (500, 560)])
rect(80, 510, 420, 100, STATUS_FILL)
centered(290, 560, "กำหนดสถานะ SENSOR_FAULT", [font_small])

# Valid sensor branch
branch_label(920, 655, "ใช่")
arrow([(900, 645), (900, 700)])
diamond(900, 785, 285, 85)
centered(900, 785, ["มี Baseline", "พร้อมใช้งานหรือไม่?"])

# Baseline not ready / warm-up branch
branch_label(1190, 735, "ไม่")
arrow([(1185, 785), (1280, 785)])
rect(1280, 735, 440, 100)
centered(1500, 785, ["สะสมค่า Warm-up", "จากข้อมูลที่เหมาะสม"], [font_small, font_small])
arrow([(1500, 835), (1500, 890)])
diamond(1500, 970, 235, 80)
centered(1500, 970, ["Warm-up", "ครบจำนวนรอบหรือไม่?"], [font_small, font_small])

# Warm-up complete
branch_label(1518, 1055, "ใช่")
arrow([(1500, 1050), (1500, 1090)])
rect(1280, 1095, 440, 100)
centered(1500, 1145, ["สร้างและบันทึก", "Baseline เริ่มต้น"], [font_small, font_small])

# Warm-up incomplete
branch_label(1740, 925, "ไม่")
arrow([(1735, 970), (1760, 970), (1760, 1275), (1725, 1275)])
rect(1280, 1225, 440, 100, STATUS_FILL)
centered(1500, 1275, "กำหนดสถานะ CALIBRATING", [font_small])

# Main evaluation path. A newly completed baseline also joins here.
branch_label(920, 875, "ใช่")
arrow([(900, 870), (900, 1410)])
arrow([(1280, 1145), (1210, 1145), (1210, 1410), (1245, 1410)])
rect(555, 1360, 690, 100)
centered(900, 1410, "คำนวณ Delta และ Rate of Change")
arrow([(900, 1460), (900, 1510)])
rect(500, 1515, 800, 125)
centered(900, 1577, ["ประเมินหลักฐานและค่าความเชื่อมั่น", "กำหนดสถานะ NORMAL, WATCH, WARNING หรือ CRITICAL"], [font, font_small])

# Merge all status paths before packet creation.
connector(900, 1740, "A")
arrow([(900, 1640), (900, 1712)])
arrow([(290, 610), (290, 1740), (872, 1740)])
arrow([(1500, 1325), (1500, 1740), (928, 1740)])
arrow([(900, 1768), (900, 1810)])

rect(560, 1815, 680, 95)
centered(900, 1862, "สร้างแพ็กเก็ต JSON")
arrow([(900, 1910), (900, 1960)])

# Retry connector R re-enters immediately before transmission.
connector(1305, 2010, "R")
arrow([(1277, 2010), (1245, 2010)])
rect(555, 1960, 690, 100)
centered(900, 2010, "สุ่มหน่วงเวลาและส่งข้อมูลผ่าน LoRa")
arrow([(900, 2060), (900, 2110)])
rect(555, 2115, 690, 100)
centered(
    900,
    2165,
    ["เปิดรับ ACK/คำสั่งจาก Gateway นาน 6 วินาที", "ตรวจสอบ ACK และประมวลผลคำสั่ง"],
    [font_small, font_small],
)
arrow([(900, 2215), (900, 2260)])

diamond(900, 2340, 255, 80)
centered(900, 2340, ["ได้รับ ACK", "ที่ตรงกับ seq หรือไม่?"], [font_small, font_small])

# ACK received
branch_label(920, 2425, "ใช่")
arrow([(900, 2420), (900, 2470)])
rect(575, 2475, 650, 100)
centered(900, 2525, "สิ้นสุดการส่งข้อมูลชุดนี้", [font_small])

# ACK not received, retry decision
branch_label(1165, 2290, "ไม่")
arrow([(1155, 2340), (1250, 2340)])
diamond(1480, 2340, 225, 80)
centered(1480, 2340, ["จำนวนครั้งที่ส่ง", "น้อยกว่า 3 ครั้งหรือไม่?"], [font_small, font_small])

branch_label(1498, 2425, "ใช่")
arrow([(1480, 2420), (1480, 2470)])
rect(1260, 2475, 440, 100)
centered(1480, 2525, "เพิ่มจำนวนครั้งที่ส่ง", [font_small])
arrow([(1700, 2525), (1732, 2525)])
connector(1760, 2525, "R")

branch_label(1715, 2290, "ไม่")
arrow([(1705, 2340), (1745, 2340), (1745, 2695), (1705, 2695)])
rect(1260, 2645, 440, 100, STATUS_FILL)
centered(1480, 2695, ["บันทึกว่าไม่ได้รับ ACK", "หลังส่งครบ 3 ครั้ง"], [font_small, font_small])

# Merge post-transmission paths.
connector(900, 2820, "B")
arrow([(900, 2575), (900, 2792)])
arrow([(1260, 2695), (1180, 2695), (1180, 2820), (928, 2820)])
arrow([(900, 2848), (900, 2890)])

# Baseline update is conditional.
diamond(900, 2970, 300, 80)
centered(
    900,
    2970,
    ["สถานะเป็น NORMAL หรือ WATCH", "ที่ไม่มีหลักฐานควันหรือไม่?"],
    [font_small, font_small],
)

branch_label(555, 2920, "ใช่")
arrow([(600, 2970), (545, 2970)])
rect(15, 2895, 530, 150)
centered(
    280,
    2970,
    ["NORMAL: ปรับอุณหภูมิ ความชื้น และควัน", "WATCH ไม่มีควัน: ปรับเฉพาะอุณหภูมิ/ความชื้น", "บันทึก NVS ทุก 144 รอบ NORMAL"],
    [font_tiny, font_tiny, font_tiny],
    [4, 4],
)

branch_label(1210, 2920, "ไม่")
arrow([(1200, 2970), (1280, 2970)])
rect(1280, 2920, 450, 100)
centered(1505, 2970, "คงค่า Baseline เดิม", [font_small])

connector(900, 3140, "C")
arrow([(280, 3045), (280, 3140), (872, 3140)])
arrow([(1505, 3020), (1505, 3140), (928, 3140)])
arrow([(900, 3168), (900, 3210)])

# Awake delay versus deep sleep.
diamond(900, 3290, 300, 80)
centered(900, 3290, ["สถานะเป็น WARNING", "หรือ CRITICAL หรือไม่?"])

branch_label(555, 3240, "ใช่")
arrow([(600, 3290), (545, 3290)])
rect(15, 3230, 530, 120)
centered(
    280,
    3290,
    ["ตื่นรอ: WARNING 60 วินาที", "CRITICAL 20 วินาที แล้วเริ่มวัดรอบใหม่"],
    [font_tiny, font_tiny],
)
arrow([(280, 3350), (280, 3400)])
connector(280, 3430, "N")

branch_label(1210, 3240, "ไม่")
arrow([(1200, 3290), (1280, 3290)])
rect(1280, 3240, 450, 100)
centered(1505, 3290, "เข้าสู่ Deep Sleep ตามสถานะ", [font_small])
arrow([(1505, 3340), (1505, 3390)])
rect(1280, 3395, 450, 100)
centered(1505, 3445, "ตื่นด้วยตัวจับเวลา", [font_small])
arrow([(1505, 3495), (1505, 3545)])
connector(1505, 3575, "I")

# Footer note explaining connector letters, kept inside the figure without a frame.
centered(
    900,
    3650,
    "จุดเชื่อม N = เริ่มรอบวัดใหม่, I = เริ่มต้นระบบหลังตื่น, R = ส่งข้อมูลซ้ำ",
    [font_small],
)

img = img.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
img.save(OUT, dpi=(300, 300))
page_img = img.crop((0, 1685, WIDTH, HEIGHT))
# The page-specific export begins at connector A. Remove incoming lines from the
# preceding section so the image can be inserted in the thesis as a clean figure.
page_draw = ImageDraw.Draw(page_img)
page_draw.rectangle((0, 0, WIDTH, 128), fill="white")
page_draw.ellipse((872, 27, 928, 83), fill="white", outline=STROKE, width=3)
page_font = ImageFont.truetype(str(FONT_PATH), 27)
page_bbox = page_draw.textbbox((0, 0), "A", font=page_font)
page_draw.text(
    (900 - (page_bbox[2] - page_bbox[0]) / 2, 55 - (page_bbox[3] - page_bbox[1]) / 2 - page_bbox[1]),
    "A",
    fill=STROKE,
    font=page_font,
)
page_draw.line((900, 83, 900, 125), fill=STROKE, width=3)
page_draw.polygon(((900, 125), (893, 110), (907, 110)), fill=STROKE)
page_img.save(PAGE_OUT, dpi=(300, 300))
print(OUT)
print(PAGE_OUT)
