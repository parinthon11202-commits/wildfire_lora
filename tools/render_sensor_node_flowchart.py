from pathlib import Path
from math import atan2, cos, sin, pi

from PIL import Image, ImageDraw, ImageFont


WIDTH, HEIGHT = 1600, 2600
SCALE = 2
OUT = Path(__file__).resolve().parents[1] / "sensor-node-flowchart-final.png"
FONT = Path(r"C:\Windows\Fonts\tahoma.ttf")


def sc(value):
    return int(round(value * SCALE))


image = Image.new("RGB", (sc(WIDTH), sc(HEIGHT)), "white")
draw = ImageDraw.Draw(image)

font_main = ImageFont.truetype(str(FONT), sc(38))
font_small = ImageFont.truetype(str(FONT), sc(31))
font_branch = ImageFont.truetype(str(FONT), sc(33))


def box(x1, y1, x2, y2):
    draw.rectangle((sc(x1), sc(y1), sc(x2), sc(y2)), fill="white", outline="#111111", width=sc(4))


def ellipse(x1, y1, x2, y2):
    draw.ellipse((sc(x1), sc(y1), sc(x2), sc(y2)), fill="white", outline="#111111", width=sc(4))


def diamond(cx, cy, half_w, half_h):
    points = [(sc(cx), sc(cy - half_h)), (sc(cx + half_w), sc(cy)),
              (sc(cx), sc(cy + half_h)), (sc(cx - half_w), sc(cy))]
    draw.polygon(points, fill="white", outline="#111111")
    draw.line(points + [points[0]], fill="#111111", width=sc(4), joint="curve")


def center_text(cx, cy, lines, fonts=None, gaps=None):
    if isinstance(lines, str):
        lines = [lines]
    if fonts is None:
        fonts = [font_main] * len(lines)
    if gaps is None:
        gaps = [10] * (len(lines) - 1)
    heights = []
    for text, font in zip(lines, fonts):
        bbox = draw.textbbox((0, 0), text, font=font)
        heights.append(bbox[3] - bbox[1])
    total = sum(heights) + sum(sc(g) for g in gaps)
    y = sc(cy) - total / 2
    for idx, (text, font, height) in enumerate(zip(lines, fonts, heights)):
        bbox = draw.textbbox((0, 0), text, font=font)
        width = bbox[2] - bbox[0]
        draw.text((sc(cx) - width / 2, y - bbox[1]), text, fill="#111111", font=font)
        y += height
        if idx < len(gaps):
            y += sc(gaps[idx])


def arrow(points):
    scaled = [(sc(x), sc(y)) for x, y in points]
    draw.line(scaled, fill="#111111", width=sc(4), joint="curve")
    (x1, y1), (x2, y2) = points[-2], points[-1]
    angle = atan2(y2 - y1, x2 - x1)
    length = 18
    spread = pi / 7
    left = (x2 - length * cos(angle - spread), y2 - length * sin(angle - spread))
    right = (x2 - length * cos(angle + spread), y2 - length * sin(angle + spread))
    draw.polygon([(sc(x2), sc(y2)), (sc(left[0]), sc(left[1])), (sc(right[0]), sc(right[1]))], fill="#111111")


ellipse(650, 28, 950, 152)
center_text(800, 90, "เริ่มต้น")
arrow([(800, 152), (800, 210)])

box(430, 215, 1170, 365)
center_text(800, 290, ["โหลด Baseline และข้อมูลจาก NVS", "เริ่มต้นเซนเซอร์ LoRa และ GPS"])
arrow([(800, 365), (800, 425)])

box(430, 430, 1170, 570)
center_text(800, 500, ["อ่านค่า SHT31 และ", "Sharp GP2Y1014AU0F"])
arrow([(800, 570), (800, 630)])

box(430, 635, 1170, 755)
center_text(800, 695, "ตรวจสอบความถูกต้องของข้อมูลเซนเซอร์")
arrow([(800, 755), (800, 815)])

box(350, 820, 1250, 985)
center_text(
    800,
    902,
    ["ตรวจสอบ Baseline", "ถ้ายังไม่พร้อมและข้อมูลเหมาะสม ให้สะสมค่า Warm-up", "ถ้าพร้อมแล้ว ให้ใช้ Baseline ที่โหลดหรือเรียนรู้ไว้"],
    [font_main, font_small, font_small],
    [8, 7],
)
arrow([(800, 985), (800, 1045)])

box(430, 1050, 1170, 1175)
center_text(800, 1112, "คำนวณ Delta และ Rate of Change")
arrow([(800, 1175), (800, 1235)])

box(300, 1240, 1300, 1420)
center_text(
    800,
    1330,
    ["ประเมินหลักฐาน ความเชื่อมั่น และสถานะ", "SENSOR_FAULT, CALIBRATING, NORMAL, WATCH,", "WARNING หรือ CRITICAL"],
    [font_main, font_small, font_small],
    [8, 7],
)
arrow([(800, 1420), (800, 1480)])

box(430, 1485, 1170, 1600)
center_text(800, 1542, "สร้างแพ็กเก็ต JSON")
arrow([(800, 1600), (800, 1660)])

box(350, 1665, 1250, 1790)
center_text(800, 1727, "สุ่มหน่วงเวลาและส่งข้อมูลผ่าน LoRa")
arrow([(800, 1790), (800, 1850)])

box(300, 1855, 1300, 2020)
center_text(
    800,
    1937,
    ["รอรับ ACK/คำสั่ง 1.8 วินาที", "หากไม่ได้รับ ACK ให้ส่งซ้ำ รวมไม่เกิน 3 ครั้ง"],
    [font_main, font_small],
    [12],
)
arrow([(800, 2020), (800, 2080)])

box(300, 2085, 1300, 2240)
center_text(
    800,
    2162,
    ["ปรับ Baseline ตามเงื่อนไข", "และบันทึกค่ารอบปัจจุบัน/บันทึก NVS ตามช่วงที่กำหนด"],
    [font_main, font_small],
    [12],
)
arrow([(800, 2240), (800, 2290)])

diamond(800, 2390, 320, 95)
center_text(800, 2390, ["สถานะเป็น WARNING", "หรือ CRITICAL หรือไม่?"])

arrow([(480, 2390), (360, 2390), (360, 2480)])
draw.text((sc(395), sc(2330)), "ใช่", fill="#111111", font=font_branch)
box(70, 2485, 650, 2580)
center_text(360, 2532, "หน่วงเวลาตามสถานะ แล้วเริ่มรอบใหม่", [font_small])
arrow([(70, 2532), (30, 2532), (30, 500), (425, 500)])

arrow([(1120, 2390), (1240, 2390), (1240, 2480)])
draw.text((sc(1165), sc(2330)), "ไม่", fill="#111111", font=font_branch)
box(950, 2485, 1530, 2580)
center_text(1240, 2532, ["เข้าสู่ Deep Sleep ตามสถานะ", "และตื่นด้วยตัวจับเวลา"], [font_small, font_small], [5])
arrow([(1530, 2532), (1570, 2532), (1570, 290), (1175, 290)])

image = image.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
image.save(OUT, dpi=(300, 300))
print(OUT)
